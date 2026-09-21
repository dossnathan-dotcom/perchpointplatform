"""Offline CSV staging only; does not create or mutate canonical records."""
import csv
import hashlib
import io
from typing import Literal

from pydantic import Field

from .base import Contract, Identifier, Record
from .property import Portfolio


class ImportBatch(Record):
    source_system: str
    source_file: str
    source_checksum: str
    organization_id: Identifier
    mapping_version: str
    status: Literal["staging", "review", "approved", "imported", "rolled_back"]
    approval_id: Identifier | None
    rollback_batch_id: Identifier | None
    immutable_report_checksum: str | None


class StagingRecord(Contract):
    row_number: int = Field(ge=2)
    source_record_identifier: str
    source_system: str
    source_file: str
    mapped_fields: dict[str, str]
    validation_result: Literal["valid", "invalid", "duplicate", "conflict"]
    issues: list[str]
    duplicate_candidate: str | None
    conflict: str | None
    correction: str | None
    approval_id: Identifier | None
    imported_canonical_record_id: Identifier | None
    rejected: bool


class Reconciliation(Contract):
    expected_rows: int
    observed_rows: int
    valid_rows: int
    rejected_rows: int
    duplicate_rows: int
    conflict_rows: int
    source_financial_total_minor: int
    staged_valid_total_minor: int
    financial_difference_minor: int
    source_document_count: int
    staged_document_count: int
    document_count_difference: int
    financial_reconciliation: Literal["review_required", "matched"]
    document_reconciliation: Literal["review_required", "matched"]


class MigrationReport(Contract):
    mapping_version: Literal["0.1.0"] = "0.1.0"
    rows: list[StagingRecord]
    control_totals: Reconciliation
    report_checksum: str
    writes_performed: Literal[0] = 0
    rollback_strategy: Literal["batch-scoped reversible mappings; compensating financial entries; never erase audits"] = "batch-scoped reversible mappings; compensating financial entries; never erase audits"


CSV_COLUMNS = ["source_system", "source_record_id", "organization_id", "property_id", "building_id", "unit_label", "use", "rent_minor", "currency", "document_count"]


def validate_import(text: str, portfolio: Portfolio, source_file: str = "synthetic-innago.csv") -> MigrationReport:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames != CSV_COLUMNS:
        raise ValueError("CSV header does not match versioned mapping")
    units = {(str(u.building_id), u.label): u for u in portfolio.units}
    buildings = {str(b.id): b for b in portfolio.buildings}
    source_seen: set[tuple[str, str]] = set()
    natural_seen: set[tuple[str, str]] = set()
    rows = []
    total = staged = source_docs = staged_docs = 0
    for number, raw in enumerate(reader, 2):
        if None in raw or any(v is None for v in raw.values()):
            raise ValueError(f"Malformed CSV row {number}")
        issues = []
        status: Literal["valid", "invalid", "duplicate", "conflict"] = "valid"
        key = (raw["source_system"], raw["source_record_id"])
        natural = (raw["building_id"], raw["unit_label"])
        duplicate = conflict = None
        try:
            rent, documents = int(raw["rent_minor"]), int(raw["document_count"])
            if rent < 0 or documents < 0:
                raise ValueError()
            total += rent
            source_docs += documents
        except ValueError:
            rent = documents = 0
            issues.append("Invalid nonnegative rent/document count")
        building = buildings.get(raw["building_id"])
        if not building or str(building.property_id) != raw["property_id"] or str(building.organization_id) != raw["organization_id"]:
            issues.append("Invalid organization/property/building chain")
        if raw["use"] not in ("residential", "commercial") or (building and raw["use"] not in building.allowed_uses):
            issues.append("Invalid unit use")
        if len(raw["currency"]) != 3 or not raw["currency"].isupper() or not raw["currency"].isalpha():
            issues.append("Invalid currency")
        if not all(raw[k].strip() for k in CSV_COLUMNS):
            issues.append("Missing required field")
        if issues:
            status = "invalid"
        elif key in source_seen or natural in natural_seen:
            status, duplicate = "duplicate", ":".join(key)
            issues.append("Repeated source or natural key; manual merge review")
        elif natural in units:
            status, conflict = "conflict", str(units[natural].id)
            issues.append("Matches existing canonical unit; explicit correction/approval required")
        source_seen.add(key)
        natural_seen.add(natural)
        if status == "valid":
            staged += rent
            staged_docs += documents
        rows.append(StagingRecord(row_number=number, source_record_identifier=raw["source_record_id"], source_system=raw["source_system"], source_file=source_file, mapped_fields=raw, validation_result=status, issues=issues, duplicate_candidate=duplicate, conflict=conflict, correction=None, approval_id=None, imported_canonical_record_id=None, rejected=status != "valid"))
    totals = Reconciliation(expected_rows=len(rows), observed_rows=len(rows), valid_rows=sum(r.validation_result == "valid" for r in rows), rejected_rows=sum(r.rejected for r in rows), duplicate_rows=sum(r.validation_result == "duplicate" for r in rows), conflict_rows=sum(r.validation_result == "conflict" for r in rows), source_financial_total_minor=total, staged_valid_total_minor=staged, financial_difference_minor=total-staged, source_document_count=source_docs, staged_document_count=staged_docs, document_count_difference=source_docs-staged_docs, financial_reconciliation="review_required" if total != staged or any(r.rejected for r in rows) else "matched", document_reconciliation="review_required" if source_docs != staged_docs or any(r.rejected for r in rows) else "matched")
    checksum = hashlib.sha256((text + totals.model_dump_json()).encode()).hexdigest()
    return MigrationReport(rows=rows, control_totals=totals, report_checksum=checksum)
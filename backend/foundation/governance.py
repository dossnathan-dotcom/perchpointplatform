from datetime import datetime
from typing import Literal

from pydantic import Field

from .base import Identifier, Record, Scope, Sensitivity

DocumentClass = Literal["application_document", "identity_document", "screening_document", "lease", "addendum", "notice", "payment_evidence", "maintenance_media", "estimate", "invoice", "insurance_policy", "vendor_credential", "inspection", "property_record", "legal_document", "communication_attachment", "migration_archive"]
DOCUMENT_CLASSES = ["application_document", "identity_document", "screening_document", "lease", "addendum", "notice", "payment_evidence", "maintenance_media", "estimate", "invoice", "insurance_policy", "vendor_credential", "inspection", "property_record", "legal_document", "communication_attachment", "migration_archive"]


class DocumentRecord(Record):
    document_class: DocumentClass
    owner_person_id: Identifier | None
    owner_organization_id: Identifier
    related_record_ids: list[Identifier]
    scope: Scope
    sensitivity: Sensitivity
    version: int = Field(ge=1)
    checksum_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source: str
    storage_reference_id: Identifier | None
    effective_at: datetime | None
    expires_at: datetime | None
    retention_rule_id: Identifier
    legal_hold: bool
    access_rule: str
    download_rule: str
    deletion_eligible: bool
    audit_required: bool


class RetentionPolicy(Record):
    version: str
    document_class: DocumentClass
    jurisdiction_policy_id: Identifier | None
    trigger_event: str
    retention_days: int | None = Field(ge=0)
    legal_review_status: Literal["qualified_review_required"]
    legal_hold_overrides_deletion: Literal[True] = True
    deletion_without_review: Literal[False] = False


class JurisdictionPolicy(Record):
    version: str
    country: str
    state: str | None
    county: str | None
    municipality: str | None
    property_id: Identifier | None
    unit_type: str | None
    lease_type: str | None
    effective_at: datetime
    expires_at: datetime | None
    policy_area: Literal["application_disclosures", "screening", "fees", "notices", "deposits", "late_payment", "maintenance", "retention", "lease_templates", "emergency_instructions"]
    approved_rule_document_id: Identifier | None
    conflict_resolution: Literal["qualified_review_required"]


class AuditEvent(Record):
    actor_id: Identifier
    effective_role: str
    delegated_authority_id: Identifier | None
    action: str
    resource_type: str
    resource_id: Identifier
    scope: Scope
    timestamp: datetime
    source_channel: Literal["web", "api", "worker", "migration", "support", "synthetic"]
    correlation_id: Identifier
    reason: str | None
    material_before: dict[str, str | int | bool | None]
    material_after: dict[str, str | int | bool | None]
    ip_device_metadata: dict[str, str]
    result: Literal["allowed", "denied", "failed", "simulated"]
    related_approval_id: Identifier | None
    related_provider_event_id: Identifier | None
    previous_event_hash: str | None
    event_hash: str
    # Append-only/WORM guarantees require future storage enforcement, not frozen models.


class DomainEvent(Record):
    domain: Literal["payment", "screening", "lease", "showing", "communication", "maintenance", "approval", "document", "migration", "account_lifecycle"]
    event_type: str
    aggregate_id: Identifier
    aggregate_version: int = Field(ge=1)
    organization_id: Identifier
    occurred_at: datetime
    correlation_id: Identifier
    causation_id: Identifier | None
    payload_record_ids: list[Identifier]


class OutboxRecord(Record):
    event: DomainEvent
    idempotency_key: str
    state: Literal["pending", "claimed", "delivered", "failed", "dead_letter"]
    attempts: int = Field(ge=0)
    next_attempt_at: datetime | None
    claim_expires_at: datetime | None
    last_error: str | None


class ProviderEvent(Record):
    integration_id: Identifier
    organization_id: Identifier
    provider_event_id: str
    received_at: datetime
    signature_verified: bool
    payload_checksum: str
    canonical_event_id: Identifier | None


class InboxRecord(Record):
    provider_event: ProviderEvent
    deduplication_key: str
    state: Literal["received", "validated", "processed", "rejected", "failed"]
    processed_at: datetime | None
    failure_code: str | None
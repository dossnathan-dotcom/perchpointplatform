"""Phase 5 commands for parties, documents, search, holds, and import staging."""
from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import zipfile
from uuid import UUID, uuid4
from xml.etree import ElementTree

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .commands import CommandError, _audit_outbox, _command
from .db import runtime_transaction
from .phase5_files import inspect_upload, object_key as allocate_object_key, read_object, write_object
from .settings import Settings

FORMULA = re.compile(r"^[=+\-@]")


def upsert_search(connection: Connection, organization: UUID, resource_type: str, resource_id: UUID, title: str, body: str, classification: str) -> None:
    connection.execute(
        text(
            """
            INSERT INTO search_documents (
              organization_id, id, resource_type, resource_id, title, body, classification, updated_at
            ) VALUES (:org, :id, :kind, :resource, :title, :body, :classification, now())
            ON CONFLICT (organization_id, resource_type, resource_id)
            DO UPDATE SET title = EXCLUDED.title, body = EXCLUDED.body,
              classification = EXCLUDED.classification, updated_at = now()
            """
        ),
        {
            "org": organization,
            "id": uuid4(),
            "kind": resource_type,
            "resource": resource_id,
            "title": title,
            "body": body,
            "classification": classification,
        },
    )


def create_party(settings: Settings, actor: UUID, organization: UUID, body: dict, key: str, correlation: UUID) -> dict:
    payload = {"party_kind": body["party_kind"], "display_name": body["display_name"]}
    return _command(settings, actor, organization, key, payload, correlation, "party.created", lambda conn, fp: _insert_party(conn, organization, actor, payload, correlation))


def _insert_party(connection: Connection, organization: UUID, actor: UUID, payload: dict, correlation: UUID) -> dict:
    party_id = uuid4()
    connection.execute(
        text("INSERT INTO parties (organization_id, id, party_kind, display_name) VALUES (:org, :id, :kind, :name)"),
        {"org": organization, "id": party_id, "kind": payload["party_kind"], "name": payload["display_name"]},
    )
    upsert_search(connection, organization, "party", party_id, payload["display_name"], payload["party_kind"], "internal")
    result = {"id": str(party_id), "version": 1}
    _audit_outbox(connection, organization, actor, "party.created", party_id, correlation, "party.created.v1", result)
    return result


def search_records(settings: Settings, actor: UUID, organization: UUID, query: str) -> dict:
    cleaned = query.strip()
    needle = cleaned.replace("%", "").replace("_", "")
    if len(cleaned) < 2 or len(needle) < 2:
        return {"results": [], "total_count": 0, "facets": []}
    params = {"query": cleaned, "needle": needle, "prefix": needle + "%", "contains": "%" + needle + "%"}
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        rows = connection.execute(
            text("SELECT * FROM perchpoint.search_rows(:query, :needle, :prefix, :contains)"),
            params,
        ).mappings().all()
        facets = connection.execute(
            text("SELECT * FROM perchpoint.search_facets(:query, :needle, :prefix, :contains)"),
            params,
        ).mappings().all()
    results = []
    for row in rows:
        title = "Restricted record" if row["classification"] == "restricted" else row["title"]
        results.append({"resource_type": row["resource_type"], "resource_id": str(row["resource_id"]), "title": title, "rank": row["rank"]})
    return {"results": results, "total_count": len(results), "facets": [{"type": row["resource_type"], "count": row["total"]} for row in facets]}


def public_search(settings: Settings, query: str) -> dict:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        rows = connection.execute(text("SELECT * FROM perchpoint.public_search(:query)"), {"query": query}).mappings().all()
    return {"results": [{"resource_type": row["resource_type"], "resource_id": str(row["resource_id"]), "title": row["title"]} for row in rows]}


def store_document(settings: Settings, actor: UUID, organization: UUID, filename: str, declared: str, data: bytes, body: dict, key: str, correlation: UUID) -> dict:
    decision = inspect_upload(filename, declared, data)
    payload = {
        "title": body["title"],
        "document_class": body["document_class"],
        "classification": body["classification"],
        "primary_resource_type": body["primary_resource_type"],
        "primary_resource_id": str(body["primary_resource_id"]),
        "filename": filename,
        "declared": declared,
        "checksum": hashlib.sha256(data).hexdigest(),
        "verdict": decision.verdict,
        "reason": decision.reason,
    }
    namespace = "accepted" if decision.verdict == "clean" else "staged" if decision.verdict == "pending_scan" else "quarantined"
    stored_key = None if decision.verdict == "rejected" else allocate_object_key(str(organization), namespace)
    return _command(
        settings,
        actor,
        organization,
        key,
        payload,
        correlation,
        "document.stored",
        lambda conn, fp: _insert_document(conn, organization, actor, payload, stored_key, data, decision.media_type, correlation),
    )


def _insert_document(connection, organization, actor, payload, object_key, data: bytes, media_type, correlation) -> dict:
    document_id = uuid4()
    if payload["verdict"] == "rejected":
        lifecycle = "rejected"
    elif payload["verdict"] == "pending_scan":
        lifecycle = "scanning"
    elif payload["verdict"] == "clean":
        lifecycle = "available"
    else:
        lifecycle = "quarantined"
    connection.execute(
        text(
            """
            INSERT INTO documents (
              organization_id, id, document_class, title, classification,
              primary_resource_type, primary_resource_id, lifecycle
            ) VALUES (:org, :id, :class, :title, :classification, :resource_type, :resource_id, :lifecycle)
            """
        ),
        {
            "org": organization,
            "id": document_id,
            "class": payload["document_class"],
            "title": payload["title"],
            "classification": payload["classification"],
            "resource_type": payload["primary_resource_type"],
            "resource_id": payload["primary_resource_id"],
            "lifecycle": lifecycle,
        },
    )
    version_id = None
    if object_key and payload["verdict"] in {"clean", "quarantined", "pending_scan"}:
        write_object(object_key, data)
    if payload["verdict"] == "pending_scan":
        connection.execute(
            text(
                """
                INSERT INTO document_jobs (
                  organization_id, id, document_id, actor_id, correlation_id, job_kind, object_key,
                  source_name, media_type, status
                ) VALUES (
                  :org, :id, :document, :actor, :correlation, 'scan', :key, :filename, :media, 'pending'
                )
                """
            ),
            {"org": organization, "id": uuid4(), "document": document_id, "actor": actor, "correlation": correlation, "key": object_key, "filename": payload["filename"], "media": media_type},
        )
    if payload["verdict"] == "clean":
        version_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO document_versions (
                  organization_id, id, document_id, version_number, object_key, checksum_sha256,
                  byte_size, media_type, original_filename, scan_verdict
                ) VALUES (:org, :id, :document, 1, :key, :checksum, :size, :media, :filename, :verdict)
                """
            ),
            {
                "org": organization,
                "id": version_id,
                "document": document_id,
                "key": object_key,
                "checksum": payload["checksum"],
                "size": len(data),
                "media": media_type,
                "filename": payload["filename"],
                "verdict": payload["verdict"],
            },
        )
        if payload["classification"] != "restricted":
            upsert_search(connection, organization, "document", document_id, payload["title"], "", payload["classification"])
        from .phase5_closeout import enqueue_processing

        enqueue_processing(connection, organization, actor, document_id, version_id, correlation)
    result = {"id": str(document_id), "lifecycle": lifecycle, "reason": payload["reason"]}
    _audit_outbox(connection, organization, actor, "document.stored", document_id, correlation, "document.stored.v1", result)
    return result


def place_hold(settings: Settings, actor: UUID, organization: UUID, document_id: UUID, body: dict, key: str, correlation: UUID) -> dict:
    payload = {"document_id": str(document_id), "reason": body["reason"]}
    return _command(settings, actor, organization, key, payload, correlation, "document.hold_placed", lambda conn, fp: _hold(conn, organization, actor, document_id, body["reason"], correlation))


def _hold(connection, organization, actor, document_id, reason, correlation) -> dict:
    found = connection.execute(text("SELECT id FROM documents WHERE organization_id = :org AND id = :id"), {"org": organization, "id": document_id}).first()
    if not found:
        raise CommandError(404, "not_found", "Document was not found")
    hold_id = uuid4()
    connection.execute(
        text("INSERT INTO legal_holds (organization_id, id, document_id, reason, placed_by) VALUES (:org, :id, :document, :reason, :actor)"),
        {"org": organization, "id": hold_id, "document": document_id, "reason": reason, "actor": actor},
    )
    connection.execute(
        text("UPDATE documents SET lifecycle = 'held', version = version + 1 WHERE organization_id = :org AND id = :id"),
        {"org": organization, "id": document_id},
    )
    result = {"id": str(hold_id), "document_id": str(document_id)}
    _audit_outbox(connection, organization, actor, "document.hold_placed", document_id, correlation, "document.hold_placed.v1", result)
    return result


def dispose_document(settings: Settings, actor: UUID, organization: UUID, document_id: UUID, body: dict, key: str, correlation: UUID) -> dict:
    if body.get("confirmation") != "destroy" or body.get("confirm_again") != "destroy":
        raise CommandError(409, "confirmation_required", "Restricted destruction requires two matching confirmations")
    payload = {"document_id": str(document_id), "expected_version": body["expected_version"]}
    return _command(settings, actor, organization, key, payload, correlation, "document.disposition_requested", lambda conn, fp: _dispose(conn, organization, actor, document_id, body, correlation))


def _dispose(connection, organization, actor, document_id, body, correlation) -> dict:
    row = connection.execute(
        text("SELECT version, lifecycle FROM documents WHERE organization_id = :org AND id = :id FOR UPDATE"),
        {"org": organization, "id": document_id},
    ).mappings().first()
    if not row:
        raise CommandError(404, "not_found", "Document was not found")
    if row["version"] != body["expected_version"]:
        raise CommandError(409, "stale_version", "The document changed. Reload and try again.", retryable=True)
    held = connection.execute(
        text("SELECT 1 FROM legal_holds WHERE organization_id = :org AND document_id = :id AND released_at IS NULL"),
        {"org": organization, "id": document_id},
    ).first()
    if held or row["lifecycle"] == "held":
        raise CommandError(409, "legal_hold", "A legal hold blocks disposition")
    if row["lifecycle"] in {"quarantined", "rejected", "disposed", "scanning", "staged"}:
        raise CommandError(409, "not_disposable", "Only an available document can be disposed")
    from .phase5_closeout import destroy_document_bytes

    destroy_document_bytes(connection, organization, document_id)
    connection.execute(
        text("UPDATE documents SET lifecycle = 'disposed', version = version + 1, published = false WHERE organization_id = :org AND id = :id"),
        {"org": organization, "id": document_id},
    )
    connection.execute(
        text("DELETE FROM search_documents WHERE organization_id = :org AND resource_type = 'document' AND resource_id = :id"),
        {"org": organization, "id": document_id},
    )
    result = {"id": str(document_id), "disposition": "disposed"}
    _audit_outbox(connection, organization, actor, "document.disposed", document_id, correlation, "document.disposed.v1", result)
    return result


def stage_import(settings: Settings, actor: UUID, organization: UUID, content: str, source_format: str, key: str, correlation: UUID) -> dict:
    payload = {"content_sha256": hashlib.sha256(content.encode()).hexdigest(), "source_format": source_format, "content": content}
    return _command(
        settings,
        actor,
        organization,
        key,
        payload,
        correlation,
        "import.staged",
        lambda conn, fp: _stage_import(conn, organization, actor, content, source_format, payload["content_sha256"], correlation),
    )


def _stage_import(connection, organization, actor, content, source_format, digest, correlation) -> dict:
    source_name, names = _import_names(content, source_format)
    batch_id = uuid4()
    connection.execute(
        text("INSERT INTO import_batches (organization_id, id, source_name, content_sha256, status) VALUES (:org, :id, :source, :digest, 'staged')"),
        {"org": organization, "id": batch_id, "source": source_name, "digest": digest},
    )
    existing = {
        value.lower()
        for value in connection.execute(
            text("SELECT display_name FROM parties WHERE organization_id = :org"),
            {"org": organization},
        ).scalars()
    }
    seen: set[str] = set()
    blockers = 0
    for index, name in enumerate(names, start=1):
        finding, detail = _classify_import(name)
        if finding == "valid" and (name.lower() in seen or name.lower() in existing):
            finding, detail = "warning", "duplicate_candidate"
        if finding == "blocker":
            blockers += 1
        if finding == "valid":
            seen.add(name.lower())
        connection.execute(
            text(
                """
                INSERT INTO import_rows (
                  organization_id, id, batch_id, source_row, raw_text, normalized_name, finding, finding_detail
                ) VALUES (:org, :id, :batch, :row, :raw, :name, :finding, :detail)
                """
            ),
            {"org": organization, "id": uuid4(), "batch": batch_id, "row": index, "raw": name, "name": name, "finding": finding, "detail": detail},
        )
    if blockers:
        from .phase5_closeout import record_quality

        record_quality(connection, organization, batch_id, "blocker", "import_blocker")
    result = {"id": str(batch_id), "status": "staged", "blockers": blockers, "source_format": source_format}
    _audit_outbox(connection, organization, actor, "import.staged", batch_id, correlation, "import.staged.v1", result)
    return result


def _import_names(content: str, source_format: str) -> tuple[str, list[str]]:
    if source_format == "csv":
        reader = csv.DictReader(io.StringIO(content))
        return "synthetic-csv", [(row.get("name") or row.get("display_name") or "").strip() for row in reader]
    if source_format == "json":
        payload = json.loads(content)
        if not isinstance(payload, list):
            raise CommandError(409, "import_format", "JSON import must be a list of records")
        return "synthetic-json", [(item.get("display_name") or item.get("name") or "").strip() for item in payload]
    if source_format == "xlsx":
        return "synthetic-xlsx", _xlsx_names(base64.b64decode(content))
    if source_format == "archive":
        return "synthetic-archive", _archive_names(base64.b64decode(content))
    raise CommandError(409, "import_format", "Unsupported import format")


def _reject_traversal(names: list[str]) -> None:
    for name in names:
        parts = name.replace("\\", "/").split("/")
        if name.startswith("/") or ".." in parts:
            raise CommandError(409, "archive_traversal", "Archive path is not allowed")


def _xlsx_names(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        _reject_traversal(archive.namelist())
        if "xl/worksheets/sheet1.xml" not in archive.namelist():
            raise CommandError(409, "import_format", "Workbook has no worksheet")
        strings: list[str] = []
        if "xl/sharedStrings.xml" in archive.namelist():
            root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
            strings = [node.text or "" for node in root.iter() if node.tag.rsplit("}", 1)[-1] == "t"]
        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        parsed: list[list[str]] = []
        for row in sheet.iter():
            if row.tag.rsplit("}", 1)[-1] != "row":
                continue
            values: list[str] = []
            for cell in list(row):
                if cell.tag.rsplit("}", 1)[-1] != "c":
                    continue
                value = ""
                for child in cell.iter():
                    if child.tag.rsplit("}", 1)[-1] == "v" and child.text:
                        value = child.text
                if cell.attrib.get("t") == "s" and value.isdigit():
                    value = strings[int(value)]
                values.append(value)
            if values:
                parsed.append(values)
    if not parsed:
        return []
    header = [item.strip().lower() for item in parsed[0]]
    column = header.index("name") if "name" in header else 0
    return [row[column].strip() if column < len(row) else "" for row in parsed[1:]]


def _archive_names(data: bytes) -> list[str]:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        _reject_traversal(archive.namelist())
        if "rows.csv" not in archive.namelist():
            raise CommandError(409, "import_format", "Archive is missing rows.csv")
        text_value = archive.read("rows.csv").decode("utf-8")
    reader = csv.DictReader(io.StringIO(text_value))
    return [(row.get("name") or "").strip() for row in reader]


def _classify_import(name: str) -> tuple[str, str]:
    if not name:
        return "blocker", "missing_name"
    if FORMULA.match(name):
        return "blocker", "formula_injection"
    return "valid", "ready"


def apply_import(settings: Settings, actor: UUID, organization: UUID, batch_id: UUID, key: str, correlation: UUID) -> dict:
    payload = {"batch_id": str(batch_id)}
    return _command(settings, actor, organization, key, payload, correlation, "import.applied", lambda conn, fp: _apply_import(conn, organization, actor, batch_id, correlation))


def _apply_import(connection, organization, actor, batch_id, correlation) -> dict:
    batch = connection.execute(
        text("SELECT status FROM import_batches WHERE organization_id = :org AND id = :id FOR UPDATE"),
        {"org": organization, "id": batch_id},
    ).mappings().first()
    if not batch:
        raise CommandError(404, "not_found", "Import batch was not found")
    if batch["status"] == "applied":
        return {"id": str(batch_id), "status": "applied"}
    blockers = connection.execute(
        text("SELECT count(*) FROM import_rows WHERE organization_id = :org AND batch_id = :id AND finding = 'blocker'"),
        {"org": organization, "id": batch_id},
    ).scalar()
    if blockers:
        raise CommandError(409, "import_blocked", "Blockers must be resolved before apply")
    if batch["status"] != "approved":
        raise CommandError(409, "approval_required", "Apply requires an explicit approval")
    rows = connection.execute(
        text("SELECT normalized_name FROM import_rows WHERE organization_id = :org AND batch_id = :id AND finding = 'valid'"),
        {"org": organization, "id": batch_id},
    ).scalars().all()
    created = []
    for name in rows:
        party = _insert_party(connection, organization, actor, {"party_kind": "person", "display_name": name}, correlation)
        created.append(party["id"])
        connection.execute(
            text("INSERT INTO import_effects (organization_id, id, batch_id, party_id) VALUES (:org, :id, :batch, :party)"),
            {"org": organization, "id": uuid4(), "batch": batch_id, "party": party["id"]},
        )
    connection.execute(
        text("UPDATE import_batches SET status = 'applied', version = version + 1 WHERE organization_id = :org AND id = :id"),
        {"org": organization, "id": batch_id},
    )
    result = {"id": str(batch_id), "status": "applied", "created": len(created)}
    _audit_outbox(connection, organization, actor, "import.applied", batch_id, correlation, "import.applied.v1", result)
    return result


def record_digest(settings: Settings, actor: UUID, organization: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        rows = connection.execute(text("SELECT event_hash FROM audit_events WHERE organization_id = :org ORDER BY occurred_at, id"), {"org": organization}).scalars().all()
        digest = hashlib.sha256("".join(rows).encode()).hexdigest()
        connection.execute(
            text("INSERT INTO audit_digests (organization_id, id, digest, event_count) VALUES (:org, :id, :digest, :count)"),
            {"org": organization, "id": uuid4(), "digest": digest, "count": len(rows)},
        )
    return {"digest": digest, "event_count": len(rows)}


def verify_digest(expected: str, actual: str) -> dict:
    return {"matches": expected == actual}


def read_document_bytes(settings: Settings, actor: UUID, organization: UUID, document_id: UUID) -> bytes:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        row = connection.execute(
            text(
                """
                SELECT v.object_key, d.lifecycle
                FROM documents d
                JOIN document_versions v ON v.document_id = d.id AND v.organization_id = d.organization_id
                WHERE d.organization_id = :org AND d.id = :id
                ORDER BY v.version_number DESC
                LIMIT 1
                """
            ),
            {"org": organization, "id": document_id},
        ).mappings().first()
        if not row or row["lifecycle"] != "available":
            raise CommandError(404, "not_found", "Document was not found")
        _audit_outbox(connection, organization, actor, "document.read", document_id, uuid4(), "document.read.v1", {"id": str(document_id)})
        key = row["object_key"]
    return read_object(key)

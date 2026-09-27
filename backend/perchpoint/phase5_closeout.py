"""Derived documents, access, export, saved search, import control, and replay."""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import zipfile
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4
from xml.etree import ElementTree

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .commands import CommandError, _audit_outbox, _command
from .db import runtime_transaction
from .phase5 import upsert_search
from .phase5_files import (
    delete_object,
    list_objects,
    object_key,
    presign_get,
    read_object,
    store_mode,
    write_object,
)
from .settings import Settings

TAG = re.compile(r"<[^>]+>")
FORMULA = re.compile(r"^[=+\-@]")
OPERATE = {"leasing", "platform_admin"}
READ = {"leasing", "platform_admin", "owner"}


def enqueue_processing(connection, organization, actor, document_id, version_id, correlation) -> None:
    for kind in ("extract", "preview"):
        connection.execute(
            text(
                """
                INSERT INTO document_jobs (
                  organization_id, id, document_id, actor_id, correlation_id, job_kind, status
                ) VALUES (:org, :id, :document, :actor, :correlation, :kind, 'pending')
                """
            ),
            {
                "org": organization,
                "id": uuid4(),
                "document": document_id,
                "actor": actor,
                "correlation": correlation,
                "kind": kind,
            },
        )
    _ = version_id


def process_document_jobs(settings: Settings, limit: int = 10) -> dict:
    processed = 0
    for _ in range(limit):
        with runtime_transaction(settings, None, None, uuid4()) as connection:
            row = connection.execute(text("SELECT * FROM perchpoint.claim_document_job('phase5')")).mappings().first()
        if not row or not row["job_id"]:
            break
        _finish_job(settings, row)
        processed += 1
    return {"processed": processed}


def _finish_job(settings: Settings, claimed) -> None:
    actor = claimed["actor_id"]
    organization = claimed["organization_id"]
    try:
        with runtime_transaction(settings, actor, organization, claimed["job_id"]) as connection:
            job = connection.execute(
                text("SELECT * FROM document_jobs WHERE organization_id = :org AND id = :id"),
                {"org": organization, "id": claimed["job_id"]},
            ).mappings().first()
            if job["job_kind"] == "scan":
                _finish_scan(connection, organization, actor, job)
            elif job["job_kind"] == "extract":
                _finish_extract(connection, organization, job)
            elif job["job_kind"] == "preview":
                _finish_preview(connection, organization, job)
            connection.execute(
                text("UPDATE document_jobs SET status = 'done', lease_until = NULL, last_error = NULL WHERE id = :id"),
                {"id": job["id"]},
            )
    except Exception as exc:
        _fail_job(settings, actor, organization, claimed["job_id"], str(exc)[:300])


def _fail_job(settings, actor, organization, job_id, error: str) -> None:
    with runtime_transaction(settings, actor, organization, job_id) as connection:
        job = connection.execute(
            text("SELECT attempts, job_kind, document_id, object_key FROM document_jobs WHERE id = :id"),
            {"id": job_id},
        ).mappings().first()
        status = "dead" if job and job["attempts"] >= 3 else "pending"
        connection.execute(
            text(
                """
                UPDATE document_jobs
                SET status = :status, lease_until = NULL, last_error = :error,
                  available_at = now() + interval '15 seconds'
                WHERE id = :id
                """
            ),
            {"id": job_id, "status": status, "error": error},
        )
        if status == "dead" and job and job["job_kind"] == "scan":
            _quarantine_unscanned(connection, organization, job)


def _quarantine_unscanned(connection, organization, job) -> None:
    if job["object_key"]:
        try:
            data = read_object(job["object_key"])
            dest = object_key(str(organization), "quarantined")
            write_object(dest, data)
            delete_object(job["object_key"])
        except Exception:
            dest = job["object_key"]
    else:
        dest = None
    connection.execute(
        text("UPDATE documents SET lifecycle = 'quarantined' WHERE organization_id = :org AND id = :id AND lifecycle = 'scanning'"),
        {"org": organization, "id": job["document_id"]},
    )
    del dest


def _finish_scan(connection, organization, actor, job) -> None:
    from .phase5_files import _clamav_instream

    data = read_object(job["object_key"])
    host = os.environ.get("PHASE5_CLAMAV_HOST", "")
    verdict = _clamav_instream(host, int(os.environ.get("PHASE5_CLAMAV_PORT", "3310")), data) if host else "unavailable"
    if verdict == "unavailable":
        raise CommandError(503, "scanner_unavailable", "The scanner is unavailable")
    if verdict != "clean":
        _quarantine_unscanned(connection, organization, job)
        _audit_outbox(connection, organization, actor, "document.scan_quarantined", job["document_id"], job["correlation_id"], "document.scan.v1", {"verdict": verdict})
        return
    accepted = object_key(str(organization), "accepted")
    write_object(accepted, data)
    delete_object(job["object_key"])
    document = connection.execute(
        text("SELECT title, classification FROM documents WHERE organization_id = :org AND id = :id"),
        {"org": organization, "id": job["document_id"]},
    ).mappings().one()
    version_id = uuid4()
    connection.execute(
        text(
            """
            INSERT INTO document_versions (
              organization_id, id, document_id, version_number, object_key, checksum_sha256,
              byte_size, media_type, original_filename, scan_verdict
            ) VALUES (:org, :id, :document, 1, :key, :checksum, :size, :media, :filename, 'clean')
            """
        ),
        {
            "org": organization,
            "id": version_id,
            "document": job["document_id"],
            "key": accepted,
            "checksum": hashlib.sha256(data).hexdigest(),
            "size": len(data),
            "media": job["media_type"],
            "filename": job["source_name"],
        },
    )
    connection.execute(
        text("UPDATE documents SET lifecycle = 'available' WHERE organization_id = :org AND id = :id"),
        {"org": organization, "id": job["document_id"]},
    )
    if document["classification"] != "restricted":
        upsert_search(connection, organization, "document", job["document_id"], document["title"], "", document["classification"])
    enqueue_processing(connection, organization, actor, job["document_id"], version_id, job["correlation_id"])
    _audit_outbox(connection, organization, actor, "document.scan_accepted", job["document_id"], job["correlation_id"], "document.scan.v1", {"verdict": "clean"})


def _latest_version(connection, organization, document_id):
    return connection.execute(
        text(
            """
            SELECT id, object_key, media_type, original_filename
            FROM document_versions
            WHERE organization_id = :org AND document_id = :id
            ORDER BY version_number DESC
            LIMIT 1
            """
        ),
        {"org": organization, "id": document_id},
    ).mappings().first()


def _finish_extract(connection, organization, job) -> None:
    version = _latest_version(connection, organization, job["document_id"])
    if not version:
        return
    data = read_object(version["object_key"])
    extracted, engine, engine_version, status, error = _extract(version["original_filename"], version["media_type"], data)
    connection.execute(
        text(
            """
            INSERT INTO document_artifacts (
              organization_id, id, document_id, version_id, artifact_kind, engine, engine_version,
              status, machine_generated, extracted_text, error
            ) VALUES (
              :org, :id, :document, :version, 'ocr', :engine, :engine_version, :status, true, :text, :error
            )
            """
        ),
        {
            "org": organization,
            "id": uuid4(),
            "document": job["document_id"],
            "version": version["id"],
            "engine": engine,
            "engine_version": engine_version,
            "status": status,
            "text": extracted,
            "error": error,
        },
    )
    if status == "ready" and extracted:
        connection.execute(
            text(
                """
                UPDATE search_documents SET body = :body, updated_at = now()
                WHERE organization_id = :org AND resource_type = 'document' AND resource_id = :id
                """
            ),
            {"org": organization, "body": extracted, "id": job["document_id"]},
        )


def _finish_preview(connection, organization, job) -> None:
    version = _latest_version(connection, organization, job["document_id"])
    if not version:
        return
    data = read_object(version["object_key"])
    preview, engine, engine_version, status, error = _preview(version["original_filename"], data)
    key = None
    if preview:
        key = object_key(str(organization), "derived")
        write_object(key, preview)
    connection.execute(
        text(
            """
            INSERT INTO document_artifacts (
              organization_id, id, document_id, version_id, artifact_kind, object_key, page_number,
              engine, engine_version, status, machine_generated, error
            ) VALUES (
              :org, :id, :document, :version, 'preview', :key, 1, :engine, :engine_version, :status, true, :error
            )
            """
        ),
        {
            "org": organization,
            "id": uuid4(),
            "document": job["document_id"],
            "version": version["id"],
            "key": key,
            "engine": engine,
            "engine_version": engine_version,
            "status": status,
            "error": error,
        },
    )


def _extract(filename: str, media_type: str, data: bytes):
    extension = filename.lower().rsplit(".", 1)[-1]
    if extension == "pdf" or media_type == "application/pdf":
        return _extract_pdf(data)
    if extension in {"txt", "csv"}:
        return _plain(data), "text", "plain", "ready", None
    if extension == "docx":
        return _office_text(data, "word/document.xml"), "office", "xml", "ready", None
    if extension == "xlsx":
        return _office_text(data, "xl/sharedStrings.xml"), "office", "xml", "ready", None
    if extension in {"png", "jpg", "jpeg"}:
        return _ocr_image(data)
    return "", "none", "none", "unsupported", "unsupported_type"


def _extract_pdf(data: bytes):
    import fitz

    document = fitz.open(stream=data, filetype="pdf")
    try:
        if document.is_encrypted:
            return "", "pymupdf", str(fitz.version[0]), "failed", "encrypted"
        parts = []
        for index, page in enumerate(document):
            if index >= 5:
                break
            parts.append(page.get_text() or "")
        text_value = sanitize_text("\n".join(parts))
        if text_value.strip():
            return text_value, "pymupdf", str(fitz.version[0]), "ready", None
        if document.page_count:
            pixmap = document[0].get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            return _ocr_image(pixmap.tobytes("png"))
        return "", "pymupdf", str(fitz.version[0]), "failed", "empty"
    finally:
        document.close()


def _plain(data: bytes) -> str:
    return sanitize_text(data.decode("utf-8", errors="replace"))


def _office_text(data: bytes, member: str) -> str:
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if member not in archive.namelist():
            return ""
        xml = archive.read(member)
    return sanitize_text(" ".join(ElementTree.fromstring(xml).itertext()))


def _ocr_image(data: bytes):
    import shutil
    import subprocess
    import tempfile

    binary = shutil.which("tesseract")
    if binary:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as handle:
            handle.write(data)
            path = handle.name
        try:
            completed = subprocess.run([binary, path, "stdout", "--psm", "6"], check=False, capture_output=True, timeout=20)
        finally:
            os.remove(path)
        version = "local"
    else:
        image = os.environ.get("PHASE5_TESSERACT_IMAGE", "")
        if not image:
            return "", "tesseract", "absent", "failed", "ocr_engine_absent"
        completed = subprocess.run(
            ["docker", "run", "--rm", "-i", image, "tesseract", "stdin", "stdout", "--psm", "6"],
            input=data,
            check=False,
            capture_output=True,
            timeout=40,
        )
        version = image
    if completed.returncode != 0:
        return "", "tesseract", version, "failed", "ocr_failed"
    return sanitize_text(completed.stdout.decode("utf-8", errors="replace")), "tesseract", version, "ready", None


def _preview(filename: str, data: bytes):
    extension = filename.lower().rsplit(".", 1)[-1]
    if extension == "pdf":
        import fitz

        document = fitz.open(stream=data, filetype="pdf")
        try:
            if document.is_encrypted or document.page_count == 0:
                return None, "pymupdf", str(fitz.version[0]), "unsupported", "no_preview"
            pixmap = document[0].get_pixmap(matrix=fitz.Matrix(1, 1), alpha=False)
            if pixmap.width * pixmap.height > 4_000_000:
                return None, "pymupdf", str(fitz.version[0]), "failed", "preview_too_large"
            return pixmap.tobytes("png"), "pymupdf", str(fitz.version[0]), "ready", None
        finally:
            document.close()
    if extension in {"png", "jpg", "jpeg"}:
        from PIL import Image

        image = Image.open(io.BytesIO(data)).convert("RGB")
        image.thumbnail((1600, 1600))
        output = io.BytesIO()
        image.save(output, format="PNG")
        return output.getvalue(), "pillow", "image", "ready", None
    return None, "none", "none", "unsupported", "unsupported_preview"


def sanitize_text(value: str) -> str:
    cleaned = TAG.sub(" ", value)
    cleaned = "".join(ch for ch in cleaned if ch in "\n\t" or ord(ch) >= 32)
    return cleaned[:20000]


def destroy_document_bytes(connection, organization, document_id) -> None:
    rows = connection.execute(
        text(
            """
            SELECT object_key FROM document_versions WHERE organization_id = :org AND document_id = :id
            UNION
            SELECT object_key FROM document_artifacts
            WHERE organization_id = :org AND document_id = :id AND object_key IS NOT NULL
            """
        ),
        {"org": organization, "id": document_id},
    ).scalars().all()
    for key in rows:
        delete_object(key)
    connection.execute(
        text("DELETE FROM document_artifacts WHERE organization_id = :org AND document_id = :id"),
        {"org": organization, "id": document_id},
    )


def reconcile_orphans(settings: Settings, actor: UUID, organization: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        known = set(
            connection.execute(
                text(
                    """
                    SELECT object_key FROM document_versions WHERE organization_id = :org
                    UNION
                    SELECT object_key FROM document_artifacts WHERE organization_id = :org AND object_key IS NOT NULL
                    UNION
                    SELECT object_key FROM document_exports WHERE organization_id = :org
                    UNION
                    SELECT object_key FROM document_jobs WHERE organization_id = :org AND object_key IS NOT NULL AND status IN ('pending', 'leased')
                    """
                ),
                {"org": organization},
            ).scalars().all()
        )
    removed = 0
    for key in list_objects(f"org/{organization}/"):
        if key not in known and "/staged/" in key:
            delete_object(key)
            removed += 1
    return {"removed_staged": removed}


def _role(connection, actor: UUID) -> str:
    row = connection.execute(text("SELECT * FROM perchpoint.current_membership(:account)"), {"account": actor}).mappings().first()
    return "" if not row else row["role_name"]


def _require(connection, actor: UUID, allowed: set[str]) -> str:
    role = _role(connection, actor)
    if role not in allowed:
        raise CommandError(404, "not_found", "Document was not found")
    return role


def list_documents(settings: Settings, actor: UUID, organization: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, actor, READ)
        rows = connection.execute(
            text(
                """
                SELECT d.id, d.title, d.lifecycle, d.classification, d.document_class, d.published, d.version,
                  (SELECT scan_verdict FROM document_versions v
                    WHERE v.document_id = d.id AND v.organization_id = d.organization_id
                    ORDER BY version_number DESC LIMIT 1) AS scan_verdict,
                  (SELECT status FROM document_artifacts a
                    WHERE a.document_id = d.id AND a.artifact_kind = 'ocr'
                    ORDER BY created_at DESC LIMIT 1) AS extraction_status,
                  (SELECT status FROM document_artifacts a
                    WHERE a.document_id = d.id AND a.artifact_kind = 'preview'
                    ORDER BY created_at DESC LIMIT 1) AS preview_status
                FROM documents d
                ORDER BY d.created_at DESC
                LIMIT 100
                """
            )
        ).mappings().all()
    return {"documents": [dict(row) | {"id": str(row["id"])} for row in rows]}


def mint_access(settings: Settings, actor: UUID, organization: UUID, document_id: UUID, purpose: str) -> dict:
    seconds = int(os.environ.get("PHASE5_ACCESS_SECONDS", "300"))
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, actor, READ)
        row = connection.execute(
            text("SELECT lifecycle, classification, published FROM documents WHERE organization_id = :org AND id = :id"),
            {"org": organization, "id": document_id},
        ).mappings().first()
        if not row or row["lifecycle"] != "available":
            raise CommandError(404, "not_found", "Document was not found")
        if row["classification"] == "public" and not row["published"]:
            raise CommandError(404, "not_found", "Document was not found")
        version = _latest_version(connection, organization, document_id)
        if not version:
            raise CommandError(404, "not_found", "Document was not found")
        token = uuid4().hex + uuid4().hex
        digest = hashlib.sha256(token.encode()).hexdigest()
        if seconds <= 0:
            expires = datetime.now(UTC) - timedelta(seconds=1)
        else:
            expires = datetime.now(UTC) + timedelta(seconds=seconds)
        connection.execute(
            text(
                """
                INSERT INTO document_access (
                  organization_id, id, document_id, actor_id, token_hash, purpose, expires_at
                ) VALUES (:org, :id, :document, :actor, :digest, :purpose, :expires)
                """
            ),
            {
                "org": organization,
                "id": uuid4(),
                "document": document_id,
                "actor": actor,
                "digest": digest,
                "purpose": purpose,
                "expires": expires,
            },
        )
        _audit_outbox(
            connection,
            organization,
            actor,
            "document.access_minted",
            document_id,
            uuid4(),
            "document.access.v1",
            {"purpose": purpose, "expires_at": expires.isoformat()},
        )
        signed = presign_get(version["object_key"], max(seconds, 1))
    return {"expires_at": expires.isoformat(), "token": token, "presigned_url": signed}


def read_granted(settings: Settings, actor: UUID, organization: UUID, document_id: UUID, token: str, range_header: str | None) -> tuple[bytes, str]:
    digest = hashlib.sha256(token.encode()).hexdigest()
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        access = connection.execute(
            text(
                """
                SELECT expires_at FROM document_access
                WHERE organization_id = :org AND document_id = :document AND actor_id = :actor AND token_hash = :digest
                """
            ),
            {"org": organization, "document": document_id, "actor": actor, "digest": digest},
        ).mappings().first()
        if not access:
            raise CommandError(404, "not_found", "Document was not found")
        if access["expires_at"] <= datetime.now(UTC):
            raise CommandError(410, "access_expired", "Document access expired")
        version = _latest_version(connection, organization, document_id)
        document = connection.execute(
            text("SELECT lifecycle FROM documents WHERE organization_id = :org AND id = :id"),
            {"org": organization, "id": document_id},
        ).mappings().first()
        if not version or not document or document["lifecycle"] != "available":
            raise CommandError(404, "not_found", "Document was not found")
        _audit_outbox(connection, organization, actor, "document.read", document_id, uuid4(), "document.read.v1", {"range": bool(range_header)})
        key = version["object_key"]
        media = version["media_type"]
    data = read_object(key)
    if range_header:
        data = _apply_range(data, range_header)
    return data, media


def _apply_range(data: bytes, header: str) -> bytes:
    if not header.startswith("bytes="):
        return data
    start_text, _, end_text = header.removeprefix("bytes=").partition("-")
    start = int(start_text or 0)
    end = int(end_text) if end_text else len(data) - 1
    return data[start : end + 1]


def create_export(settings: Settings, actor: UUID, organization: UUID, document_ids: list[UUID], key: str, correlation: UUID) -> dict:
    payload = {"documents": [str(item) for item in document_ids]}
    return _command(settings, actor, organization, key, payload, correlation, "document.exported", lambda conn, fp: _export(conn, organization, actor, document_ids, correlation))


def _export(connection, organization, actor, document_ids, correlation) -> dict:
    _require(connection, actor, OPERATE)
    if len(document_ids) > 20:
        raise CommandError(409, "export_limited", "Export volume exceeds the local limit")
    export_id = uuid4()
    included = []
    archive = io.BytesIO()
    with zipfile.ZipFile(archive, "w") as bundle:
        for document_id in document_ids:
            row = connection.execute(
                text("SELECT lifecycle, title FROM documents WHERE organization_id = :org AND id = :id"),
                {"org": organization, "id": document_id},
            ).mappings().first()
            version = _latest_version(connection, organization, document_id) if row else None
            if not row or row["lifecycle"] != "available" or not version:
                continue
            data = read_object(version["object_key"])
            safe_name = f"{document_id}.bin"
            bundle.writestr(safe_name, data)
            included.append({"document_id": str(document_id), "version_id": str(version["id"]), "sha256": hashlib.sha256(data).hexdigest()})
        manifest = {
            "export_id": str(export_id),
            "organization_id": str(organization),
            "actor_id": str(actor),
            "records": included,
            "created_at": datetime.now(UTC).isoformat(),
            "policy": "phase5-provisional",
        }
        bundle.writestr("manifest.json", json.dumps(manifest))
        bundle.writestr("records.csv", _safe_csv(included))
    if not included:
        raise CommandError(404, "not_found", "Document was not found")
    key = object_key(str(organization), "exports")
    write_object(key, archive.getvalue())
    expires = datetime.now(UTC) + timedelta(minutes=5)
    connection.execute(
        text(
            """
            INSERT INTO document_exports (
              organization_id, id, actor_id, scope, manifest, object_key, status, expires_at
            ) VALUES (:org, :id, :actor, CAST(:scope AS jsonb), CAST(:manifest AS jsonb), :key, 'ready', :expires)
            """
        ),
        {
            "org": organization,
            "id": export_id,
            "actor": actor,
            "scope": json.dumps({"documents": [str(item) for item in document_ids]}),
            "manifest": json.dumps(manifest),
            "key": key,
            "expires": expires,
        },
    )
    _audit_outbox(connection, organization, actor, "document.exported", export_id, correlation, "document.exported.v1", {"count": len(included)})
    return {"id": str(export_id), "count": len(included), "expires_at": expires.isoformat(), "role": _role(connection, actor)}


def read_export(settings: Settings, actor: UUID, organization: UUID, export_id: UUID) -> tuple[bytes, dict]:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, actor, READ)
        row = connection.execute(
            text(
                """
                SELECT actor_id, manifest, object_key, status, expires_at
                FROM document_exports
                WHERE organization_id = :org AND id = :id
                """
            ),
            {"org": organization, "id": export_id},
        ).mappings().first()
        if not row:
            raise CommandError(404, "not_found", "Export was not found")
        if row["expires_at"] <= datetime.now(UTC) or row["status"] != "ready":
            delete_object(row["object_key"])
            connection.execute(
                text("UPDATE document_exports SET status = 'expired' WHERE organization_id = :org AND id = :id"),
                {"org": organization, "id": export_id},
            )
            raise CommandError(410, "export_expired", "Export access expired")
        _audit_outbox(connection, organization, actor, "document.export_read", export_id, uuid4(), "document.export_read.v1", {"expired": False})
        key = row["object_key"]
        manifest = row["manifest"]
    return read_object(key), manifest


def _safe_csv(rows: list[dict]) -> str:
    lines = ["document_id,sha256"]
    for row in rows:
        values = []
        for value in (row["document_id"], row["sha256"]):
            text_value = str(value)
            if FORMULA.match(text_value):
                text_value = "'" + text_value
            values.append(text_value)
        lines.append(",".join(values))
    return "\n".join(lines)


def save_search(settings: Settings, actor: UUID, organization: UUID, name: str, query: str, key: str, correlation: UUID) -> dict:
    payload = {"name": name, "query": query}
    return _command(settings, actor, organization, key, payload, correlation, "search.saved", lambda conn, fp: _save_search(conn, organization, actor, name, query, correlation))


def _save_search(connection, organization, actor, name, query, correlation) -> dict:
    _require(connection, actor, READ)
    search_id = uuid4()
    connection.execute(
        text(
            """
            INSERT INTO saved_searches (organization_id, id, actor_id, query_text, name, visibility, shared)
            VALUES (:org, :id, :actor, :query, :name, 'private', false)
            """
        ),
        {"org": organization, "id": search_id, "actor": actor, "query": query, "name": name},
    )
    result = {"id": str(search_id), "visibility": "private"}
    _audit_outbox(connection, organization, actor, "search.saved", search_id, correlation, "search.saved.v1", result)
    return result


def share_search(settings: Settings, actor: UUID, organization: UUID, search_id: UUID, visibility: str, key: str, correlation: UUID) -> dict:
    if visibility not in {"private", "organization"}:
        raise CommandError(409, "visibility_invalid", "Sharing must be private or organization")
    payload = {"id": str(search_id), "visibility": visibility}
    return _command(settings, actor, organization, key, payload, correlation, "search.shared", lambda conn, fp: _share_search(conn, organization, actor, search_id, visibility, correlation))


def _share_search(connection, organization, actor, search_id, visibility, correlation) -> dict:
    updated = connection.execute(
        text(
            """
            UPDATE saved_searches SET visibility = :visibility, shared = :shared
            WHERE organization_id = :org AND id = :id AND actor_id = :actor
            """
        ),
        {"org": organization, "id": search_id, "actor": actor, "visibility": visibility, "shared": visibility == "organization"},
    )
    if updated.rowcount != 1:
        raise CommandError(404, "not_found", "Saved search was not found")
    result = {"id": str(search_id), "visibility": visibility}
    _audit_outbox(connection, organization, actor, "search.share_changed", search_id, correlation, "search.shared.v1", result)
    return result


def list_saved(settings: Settings, actor: UUID, organization: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, actor, READ)
        rows = connection.execute(
            text("SELECT id, name, query_text, visibility FROM saved_searches ORDER BY created_at DESC")
        ).mappings().all()
    return {"saved": [{"id": str(row["id"]), "name": row["name"], "query": row["query_text"], "visibility": row["visibility"]} for row in rows]}


def delete_saved(settings: Settings, actor: UUID, organization: UUID, search_id: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        deleted = connection.execute(
            text("DELETE FROM saved_searches WHERE organization_id = :org AND id = :id AND actor_id = :actor"),
            {"org": organization, "id": search_id, "actor": actor},
        )
        if deleted.rowcount != 1:
            raise CommandError(404, "not_found", "Saved search was not found")
    return {"id": str(search_id), "deleted": True}


def update_saved(settings: Settings, actor: UUID, organization: UUID, search_id: UUID, name: str, query: str, key: str, correlation: UUID) -> dict:
    payload = {"id": str(search_id), "name": name, "query": query}
    return _command(settings, actor, organization, key, payload, correlation, "search.updated", lambda conn, fp: _update_saved(conn, organization, actor, search_id, name, query, correlation))


def _update_saved(connection, organization, actor, search_id, name, query, correlation) -> dict:
    updated = connection.execute(
        text(
            """
            UPDATE saved_searches SET name = :name, query_text = :query
            WHERE organization_id = :org AND id = :id AND actor_id = :actor
            """
        ),
        {"org": organization, "id": search_id, "actor": actor, "name": name, "query": query},
    )
    if updated.rowcount != 1:
        raise CommandError(404, "not_found", "Saved search was not found")
    result = {"id": str(search_id), "name": name, "query": query}
    _audit_outbox(connection, organization, actor, "search.updated", search_id, correlation, "search.updated.v1", result)
    return result


def duplicate_saved(settings: Settings, actor: UUID, organization: UUID, search_id: UUID, key: str, correlation: UUID) -> dict:
    payload = {"id": str(search_id)}
    return _command(settings, actor, organization, key, payload, correlation, "search.duplicated", lambda conn, fp: _duplicate_saved(conn, organization, actor, search_id, correlation))


def _duplicate_saved(connection, organization, actor, search_id, correlation) -> dict:
    row = connection.execute(
        text("SELECT name, query_text FROM saved_searches WHERE organization_id = :org AND id = :id AND actor_id = :actor"),
        {"org": organization, "id": search_id, "actor": actor},
    ).mappings().first()
    if not row:
        raise CommandError(404, "not_found", "Saved search was not found")
    return _save_search(connection, organization, actor, row["name"] + " copy", row["query_text"], correlation)


def approve_import(settings: Settings, actor: UUID, organization: UUID, batch_id: UUID, key: str, correlation: UUID) -> dict:
    payload = {"batch_id": str(batch_id)}
    return _command(settings, actor, organization, key, payload, correlation, "import.approved", lambda conn, fp: _approve_import(conn, organization, actor, batch_id, correlation))


def _approve_import(connection, organization, actor, batch_id, correlation) -> dict:
    _require(connection, actor, OPERATE)
    blockers = connection.execute(
        text("SELECT count(*) FROM import_rows WHERE organization_id = :org AND batch_id = :id AND finding = 'blocker'"),
        {"org": organization, "id": batch_id},
    ).scalar()
    if blockers:
        raise CommandError(409, "import_blocked", "Blockers must be resolved before approval")
    updated = connection.execute(
        text(
            """
            UPDATE import_batches SET status = 'approved', approved_by = :actor, version = version + 1
            WHERE organization_id = :org AND id = :id AND status IN ('staged', 'dry_run')
            """
        ),
        {"org": organization, "id": batch_id, "actor": actor},
    )
    if updated.rowcount != 1:
        raise CommandError(409, "approval_conflict", "The import is not waiting for approval")
    result = {"id": str(batch_id), "status": "approved"}
    _audit_outbox(connection, organization, actor, "import.approved", batch_id, correlation, "import.approved.v1", result)
    return result


def dry_run_import(settings: Settings, actor: UUID, organization: UUID, batch_id: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, actor, OPERATE)
        counts = connection.execute(
            text("SELECT finding, count(*) FROM import_rows WHERE organization_id = :org AND batch_id = :id GROUP BY finding"),
            {"org": organization, "id": batch_id},
        ).all()
        connection.execute(
            text("UPDATE import_batches SET status = 'dry_run' WHERE organization_id = :org AND id = :id AND status = 'staged'"),
            {"org": organization, "id": batch_id},
        )
    return {"id": str(batch_id), "findings": {row[0]: row[1] for row in counts}}


def rollback_import(settings: Settings, actor: UUID, organization: UUID, batch_id: UUID, key: str, correlation: UUID) -> dict:
    payload = {"batch_id": str(batch_id)}
    return _command(settings, actor, organization, key, payload, correlation, "import.rolled_back", lambda conn, fp: _rollback_import(conn, organization, actor, batch_id, correlation))


def _rollback_import(connection, organization, actor, batch_id, correlation) -> dict:
    _require(connection, actor, OPERATE)
    batch = connection.execute(
        text("SELECT status FROM import_batches WHERE organization_id = :org AND id = :id FOR UPDATE"),
        {"org": organization, "id": batch_id},
    ).mappings().first()
    if not batch or batch["status"] != "applied":
        raise CommandError(409, "rollback_unavailable", "Only an applied import can be rolled back")
    parties = connection.execute(
        text("SELECT party_id FROM import_effects WHERE organization_id = :org AND batch_id = :id"),
        {"org": organization, "id": batch_id},
    ).scalars().all()
    for party_id in parties:
        connection.execute(
            text("DELETE FROM search_documents WHERE organization_id = :org AND resource_type = 'party' AND resource_id = :id"),
            {"org": organization, "id": party_id},
        )
        connection.execute(
            text("DELETE FROM parties WHERE organization_id = :org AND id = :id"),
            {"org": organization, "id": party_id},
        )
    connection.execute(
        text("UPDATE import_batches SET status = 'rolled_back', version = version + 1 WHERE organization_id = :org AND id = :id"),
        {"org": organization, "id": batch_id},
    )
    result = {"id": str(batch_id), "status": "rolled_back", "removed": len(parties)}
    _audit_outbox(connection, organization, actor, "import.rolled_back", batch_id, correlation, "import.rolled_back.v1", result)
    return result


def import_report(settings: Settings, actor: UUID, organization: UUID, batch_id: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, actor, READ)
        batch = connection.execute(
            text("SELECT status, content_sha256, mapping_version FROM import_batches WHERE organization_id = :org AND id = :id"),
            {"org": organization, "id": batch_id},
        ).mappings().first()
        if not batch:
            raise CommandError(404, "not_found", "Import batch was not found")
        counts = connection.execute(
            text("SELECT finding, count(*) FROM import_rows WHERE organization_id = :org AND batch_id = :id GROUP BY finding"),
            {"org": organization, "id": batch_id},
        ).all()
    return {
        "id": str(batch_id),
        "status": batch["status"],
        "checksum": batch["content_sha256"],
        "mapping_version": batch["mapping_version"],
        "findings": {row[0]: row[1] for row in counts},
    }


def list_quality(settings: Settings, actor: UUID, organization: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        role = _require(connection, actor, READ)
        clause = "AND severity = 'blocker'" if role == "owner" else ""
        rows = connection.execute(
            text(
                f"""
                SELECT id, resource_type, resource_id, severity, detail, rule_version, resolution, source_evidence
                FROM quality_findings
                WHERE resolution IS NULL {clause}
                ORDER BY severity, id
                LIMIT 100
                """
            )
        ).mappings().all()
    return {
        "findings": [
            {
                "id": str(row["id"]),
                "resource_type": row["resource_type"],
                "resource_id": str(row["resource_id"]),
                "severity": row["severity"],
                "detail": row["detail"],
                "rule_version": row["rule_version"],
                "source_evidence": row["source_evidence"],
            }
            for row in rows
        ]
    }


def resolve_quality(settings: Settings, actor: UUID, organization: UUID, finding_id: UUID, reason: str, key: str, correlation: UUID) -> dict:
    payload = {"id": str(finding_id), "reason": reason}
    return _command(settings, actor, organization, key, payload, correlation, "quality.resolved", lambda conn, fp: _resolve_quality(conn, organization, actor, finding_id, reason, correlation))


def _resolve_quality(connection, organization, actor, finding_id, reason, correlation) -> dict:
    _require(connection, actor, OPERATE)
    updated = connection.execute(
        text(
            """
            UPDATE quality_findings SET resolution = :reason, resolved_by = :actor
            WHERE organization_id = :org AND id = :id AND resolution IS NULL
            """
        ),
        {"org": organization, "id": finding_id, "actor": actor, "reason": reason},
    )
    if updated.rowcount != 1:
        raise CommandError(404, "not_found", "Quality finding was not found")
    result = {"id": str(finding_id), "resolution": reason}
    _audit_outbox(connection, organization, actor, "quality.resolved", finding_id, correlation, "quality.resolved.v1", result)
    return result


def list_audit(settings: Settings, actor: UUID, organization: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        role = _require(connection, actor, READ)
        rows = connection.execute(
            text(
                """
                SELECT id, actor_id, action, resource_type, resource_id, occurred_at, correlation_id, result, redacted
                FROM audit_events
                ORDER BY occurred_at DESC
                LIMIT 50
                """
            )
        ).mappings().all()
        digest = connection.execute(
            text("SELECT digest, event_count FROM audit_digests ORDER BY created_at DESC LIMIT 1")
        ).mappings().first()
    events = []
    for row in rows:
        if role == "owner" and row["action"] not in {"document.disposed", "document.hold_placed", "quality.resolved", "document.exported"}:
            continue
        events.append(
            {
                "id": str(row["id"]),
                "actor_id": None if row["actor_id"] is None else str(row["actor_id"]),
                "action": row["action"],
                "resource_id": str(row["resource_id"]),
                "occurred_at": row["occurred_at"].isoformat(),
                "correlation_id": str(row["correlation_id"]),
                "result": row["result"],
                "redacted": row["redacted"],
            }
        )
    return {"events": events, "digest": None if not digest else {"digest": digest["digest"], "event_count": digest["event_count"]}}


def replay_projection(settings: Settings, actor: UUID, organization: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, actor, {"platform_admin"})
        connection.execute(text("DELETE FROM search_documents WHERE organization_id = :org"), {"org": organization})
        connection.execute(
            text(
                """
                INSERT INTO search_documents (organization_id, id, resource_type, resource_id, title, body, classification)
                SELECT organization_id, gen_random_uuid(), 'party', id, display_name, party_kind, 'internal' FROM parties
                WHERE organization_id = :org
                """
            ),
            {"org": organization},
        )
        connection.execute(
            text(
                """
                INSERT INTO search_documents (organization_id, id, resource_type, resource_id, title, body, classification)
                SELECT organization_id, gen_random_uuid(), 'property', id, name, property_type, 'internal'
                FROM properties WHERE organization_id = :org
                """
            ),
            {"org": organization},
        )
        connection.execute(
            text(
                """
                INSERT INTO search_documents (organization_id, id, resource_type, resource_id, title, body, classification)
                SELECT organization_id, gen_random_uuid(), 'listing', id, property_name || ' ' || label, publication,
                  CASE WHEN publication = 'published' THEN 'public' ELSE 'internal' END
                FROM listings WHERE organization_id = :org
                """
            ),
            {"org": organization},
        )
        connection.execute(
            text(
                """
                INSERT INTO search_documents (organization_id, id, resource_type, resource_id, title, body, classification)
                SELECT d.organization_id, gen_random_uuid(), 'document', d.id, d.title, coalesce(a.extracted_text, ''), d.classification
                FROM documents d
                LEFT JOIN LATERAL (
                  SELECT extracted_text FROM document_artifacts
                  WHERE document_id = d.id AND artifact_kind = 'ocr' AND status = 'ready'
                  ORDER BY created_at DESC LIMIT 1
                ) a ON true
                WHERE d.organization_id = :org AND d.lifecycle = 'available' AND d.classification <> 'restricted'
                """
            ),
            {"org": organization},
        )
        actual = connection.execute(text("SELECT count(*) FROM search_documents WHERE organization_id = :org"), {"org": organization}).scalar()
        expected = connection.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM parties WHERE organization_id = :org) +
                  (SELECT count(*) FROM properties WHERE organization_id = :org) +
                  (SELECT count(*) FROM listings WHERE organization_id = :org) +
                  (SELECT count(*) FROM documents WHERE organization_id = :org AND lifecycle = 'available' AND classification <> 'restricted')
                """
            ),
            {"org": organization},
        ).scalar()
        status = "reconciled" if actual == expected else "dead"
        connection.execute(
            text(
                """
                INSERT INTO replay_runs (organization_id, id, actor_id, status, expected_count, actual_count, detail)
                VALUES (:org, :id, :actor, :status, :expected, :actual, 'projection rebuilt from canonical rows')
                """
            ),
            {"org": organization, "id": uuid4(), "actor": actor, "status": status, "expected": expected, "actual": actual},
        )
    return {"status": status, "expected": expected, "actual": actual}


def diagnostics(settings: Settings, actor: UUID, organization: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, actor, {"platform_admin"})
        dead = connection.execute(text("SELECT count(*) FROM document_jobs WHERE status = 'dead'")).scalar()
        leased = connection.execute(text("SELECT count(*) FROM document_jobs WHERE status = 'leased' AND lease_until < now()")).scalar()
    return {
        "object_store": store_mode(),
        "scanner_mode": os.environ.get("PHASE5_SCANNER_MODE", "live"),
        "dead_jobs": dead,
        "expired_leases": leased,
        "bucket": os.environ.get("PHASE5_S3_BUCKET", "perchpoint-documents") if store_mode() == "s3" else "filesystem",
    }


def record_quality(connection: Connection, organization, resource_id, severity: str, detail: str) -> None:
    connection.execute(
        text(
            """
            INSERT INTO quality_findings (
              organization_id, id, resource_type, resource_id, severity, detail, rule_version, source_evidence
            ) VALUES (:org, :id, 'import', :resource, :severity, :detail, 'phase5-1', 'import row')
            """
        ),
        {"org": organization, "id": uuid4(), "resource": resource_id, "severity": severity, "detail": detail},
    )

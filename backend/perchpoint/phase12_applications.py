"""Phase 12 applications. Submission is immutable. Screening, leases, and payments stay out."""
from __future__ import annotations

import hashlib
import json
import re
import secrets
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .db import runtime_transaction
from .settings import Settings


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _call(connection, statement: str, params: dict) -> dict:
    row = connection.execute(text(statement), params).scalar_one()
    if not row["accepted"]:
        status = 409 if row["code"] in {"conflict", "incomplete", "unavailable"} else 400
        raise CommandError(status, row["code"], "The application request could not be accepted.", False)
    return row


def start(settings: Settings, payload: dict, idempotency_key: str) -> dict:
    if any(payload.get(name) for name in ("ssn", "credit_score", "criminal_history", "screening", "lease", "payment_token")):
        raise CommandError(400, "rejected", "The application request could not be accepted.", False)
    token = secrets.token_urlsafe(32)
    body = {
        "receipt": payload.get("receipt") or "",
        "disclosure": "true" if payload.get("disclosure") else "",
        "application_type": payload.get("application_type") or "residential",
        "preferred_name": payload.get("preferred_name") or "",
        "legal_name": payload.get("legal_name") or "",
        "email": payload.get("email") or "",
        "showing_reference": payload.get("showing_reference") or "",
    }
    fingerprint = hashlib.sha256(repr(sorted(body.items())).encode()).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.start_application(CAST(:intake AS jsonb), CAST(:key AS text), CAST(:fingerprint AS text), CAST(:token_hash AS text))",
            {"intake": json.dumps(body), "key": idempotency_key, "fingerprint": fingerprint, "token_hash": _hash(token)},
        )
    result = {"accepted": True, "reference": row["reference"], "replayed": row["replayed"], "state": row.get("state") or "draft"}
    if not row["replayed"]:
        result["capability"] = token
    return result


def save_answer(settings: Settings, capability: str, field_code: str, field_value: str, expected_version: int) -> dict:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.save_application_answer(CAST(:token_hash AS text), CAST(:field_code AS text), CAST(:field_value AS text), CAST(:expected_version AS integer))",
            {"token_hash": _hash(capability), "field_code": field_code, "field_value": field_value, "expected_version": expected_version},
        )
    return {"accepted": True, "version": row["version"]}


def finalize_document(settings: Settings, capability: str, document_class: str, display_name: str, content: str, magic: str) -> dict:
    cleaned = re.sub(r"[\x00-\x1f<>]", "", display_name.rsplit("/", 1)[-1].rsplit("\\", 1)[-1])[:80]
    suspicious = magic not in {"JFIF", "PDF"} or "EICAR" in content or "<script" in content.lower()
    digest = hashlib.sha256(content.encode()).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.finalize_application_document(CAST(:token_hash AS text), CAST(:document_class AS text), CAST(:display_name AS text), CAST(:content_hash AS text), CAST(:byte_size AS integer), CAST(:magic AS text), CAST(:suspicious AS boolean))",
            {
                "token_hash": _hash(capability),
                "document_class": document_class,
                "display_name": cleaned or "document",
                "content_hash": digest,
                "byte_size": max(len(content.encode()), 1),
                "magic": magic if magic in {"JFIF", "PDF"} else "REJECT",
                "suspicious": suspicious,
            },
        )
    return {"accepted": True, "scan_state": row["scan_state"]}


def submit(settings: Settings, capability: str, idempotency_key: str, expected_version: int, attestation: bool) -> dict:
    if not attestation:
        raise CommandError(400, "rejected", "The application request could not be accepted.", False)
    fingerprint = hashlib.sha256(f"{_hash(capability)}:{expected_version}".encode()).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.submit_application(CAST(:token_hash AS text), CAST(:key AS text), CAST(:fingerprint AS text), CAST(:expected_version AS integer))",
            {"token_hash": _hash(capability), "key": idempotency_key, "fingerprint": fingerprint, "expected_version": expected_version},
        )
    return {"accepted": True, "reference": row["reference"], "replayed": row["replayed"], "state": "submitted", "snapshot_hash": row.get("snapshot_hash")}


def withdraw(settings: Settings, capability: str) -> dict:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.withdraw_application(CAST(:token_hash AS text))",
            {"token_hash": _hash(capability)},
        )
    return {"accepted": True, "reference": row["reference"], "state": "withdrawn"}


def invite(settings: Settings, capability: str, role_name: str, destination_email: str) -> dict:
    if role_name == "minor_occupant":
        raise CommandError(400, "rejected", "The application request could not be accepted.", False)
    token = secrets.token_urlsafe(32)
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        _call(
            connection,
            "SELECT perchpoint.invite_application_participant(CAST(:token_hash AS text), CAST(:role_name AS text), CAST(:email AS text), CAST(:invite_hash AS text))",
            {"token_hash": _hash(capability), "role_name": role_name, "email": destination_email, "invite_hash": _hash(token)},
        )
    return {"accepted": True, "invitation": token, "state": "pending"}


def add_minor(settings: Settings, actor, organization, reference: str, preferred_name: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(text("SELECT id FROM applications WHERE public_reference = :reference"), {"reference": reference}).first()
        if row is None:
            raise CommandError(404, "not_found", "The application was not found.", False)
        connection.execute(
            text(
                "INSERT INTO application_participants (organization_id, id, application_id, role_name, preferred_name) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :application, 'minor_occupant', :name)"
            ),
            {"org": organization, "application": row.id, "name": preferred_name[:120]},
        )
    return {"role": "minor_occupant"}


def request_item(settings: Settings, actor, organization, reference: str, field_code: str) -> dict:
    if field_code in {"ssn", "credit_score", "criminal_history"}:
        raise CommandError(400, "rejected", "The application request could not be accepted.", False)
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(text("SELECT id FROM applications WHERE public_reference = :reference"), {"reference": reference}).first()
        if row is None:
            raise CommandError(404, "not_found", "The application was not found.", False)
        connection.execute(
            text(
                "INSERT INTO application_requests (organization_id, id, application_id, field_code, due_at, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :application, :field_code, now() + interval '3 days', 'open')"
            ),
            {"org": organization, "application": row.id, "field_code": field_code},
        )
    return {"state": "open"}


def handoff(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(text("SELECT id, state FROM applications WHERE public_reference = :reference"), {"reference": reference}).first()
        if row is None:
            raise CommandError(404, "not_found", "The application was not found.", False)
        if row.state != "submitted":
            raise CommandError(409, "conflict", "The application is not ready for a technical handoff.", False)
        connection.execute(
            text("UPDATE applications SET state = 'ready_for_screening', version = version + 1 WHERE id = :id"),
            {"id": row.id},
        )
        connection.execute(
            text("INSERT INTO application_events (organization_id, id, application_id, event_kind) VALUES (CAST(:org AS uuid), gen_random_uuid(), :application, 'handoff')"),
            {"org": organization, "application": row.id},
        )
    return {"state": "ready_for_screening"}


def place_hold(settings: Settings, actor, organization, reference: str, reason: str) -> dict:
    try:
        with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
            _require(connection, "inquiry.manage")
            row = connection.execute(text("SELECT id FROM applications WHERE public_reference = :reference"), {"reference": reference}).first()
            if row is None:
                raise CommandError(404, "not_found", "The application was not found.", False)
            connection.execute(
                text(
                    "INSERT INTO application_legal_holds (organization_id, id, application_id, reason) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :application, :reason)"
                ),
                {"org": organization, "application": row.id, "reason": reason[:200]},
            )
    except IntegrityError as exc:
        raise CommandError(409, "conflict", "The application request could not be accepted.", False) from exc
    return {"held": True}

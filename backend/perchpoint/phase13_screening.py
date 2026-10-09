"""Phase 13 screening. Providers supply fake evidence. A person records the decision."""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
from uuid import UUID, uuid4

from sqlalchemy import text

from .commands import CommandError
from .db import runtime_transaction
from .settings import Settings

_CRIMINAL_REJECTS = {"arrest_only", "blanket_felony", "sealed", "name_only", "unofficial"}


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
        status = 409 if row["code"] in {"conflict", "incomplete"} else 400
        raise CommandError(status, row["code"], "The screening request could not be accepted.", False)
    return row


def criminal_safeguard(record_kind: str) -> dict:
    if record_kind in _CRIMINAL_REJECTS:
        return {"accepted": False, "code": "disabled"}
    if record_kind == "test_only_individualized":
        return {"accepted": True, "ordered": False, "result": "individualized_review_required"}
    return {"accepted": False, "code": "disabled"}


def open_case(settings: Settings, actor, organization, application_reference: str, idempotency_key: str) -> dict:
    token = secrets.token_urlsafe(32)
    fingerprint = hashlib.sha256(f"{application_reference}:{organization}".encode()).hexdigest()
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = _call(
            connection,
            "SELECT perchpoint.open_screening_case(CAST(:reference AS text), CAST(:caller_org AS uuid), CAST(:key AS text), CAST(:fingerprint AS text), CAST(:token_hash AS text))",
            {
                "reference": application_reference,
                "caller_org": organization,
                "key": idempotency_key,
                "fingerprint": fingerprint,
                "token_hash": _hash(token),
            },
        )
    result = {"accepted": True, "reference": row["reference"], "replayed": row["replayed"], "state": row.get("state") or "awaiting_authorization"}
    if not row["replayed"]:
        result["capability"] = token
    return result


def grant_authorization(settings: Settings, capability: str) -> dict:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.grant_screening_authorization(CAST(:token_hash AS text))",
            {"token_hash": _hash(capability)},
        )
    return {"accepted": True, "state": row["state"]}


def place_order(settings: Settings, capability: str, product: str, idempotency_key: str) -> dict:
    if product == "criminal" or product not in {"credit", "income", "rental"}:
        raise CommandError(400, "rejected", "The screening request could not be accepted.", False)
    fingerprint = hashlib.sha256(f"{_hash(capability)}:{product}".encode()).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.place_screening_order(CAST(:token_hash AS text), CAST(:product AS text), CAST(:key AS text), CAST(:fingerprint AS text))",
            {"token_hash": _hash(capability), "product": product, "key": idempotency_key, "fingerprint": fingerprint},
        )
    return {"accepted": True, "reference": row["reference"], "replayed": row["replayed"], "state": "awaiting_results", "product": product}


def apply_result(settings: Settings, capability: str, body: bytes, signature: str, coverage: str) -> dict:
    expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        raise CommandError(400, "rejected", "The screening request could not be accepted.", False)
    payload = json.loads(body.decode())
    if payload.get("ssn") or payload.get("criminal_history"):
        raise CommandError(400, "rejected", "The screening request could not be accepted.", False)
    event_hash = hashlib.sha256(capability.encode() + b"\n" + body).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.apply_screening_result(CAST(:token_hash AS text), CAST(:event_hash AS text), CAST(:coverage AS text))",
            {"token_hash": _hash(capability), "event_hash": event_hash, "coverage": coverage},
        )
    return {"accepted": True, "replayed": row["replayed"], "state": "ready_for_review"}


def record_decision(settings: Settings, actor, organization, reference: str, outcome: str, human_confirmed: bool) -> dict:
    if not human_confirmed or outcome not in {"approved", "conditional", "denied", "unable_to_complete"}:
        raise CommandError(400, "rejected", "The screening request could not be accepted.", False)
    notice_kind = "adverse_action" if outcome in {"denied", "conditional"} else "non_fcra"
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text("SELECT id, state FROM screening_cases WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "not_found", "The screening case was not found.", False)
        if row.state != "ready_for_review":
            raise CommandError(409, "conflict", "The screening case is not ready for a decision.", False)
        connection.execute(
            text(
                "INSERT INTO screening_decisions (organization_id, id, case_id, outcome, human_confirmed, basis_code) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :case_id, :outcome, true, 'policy_v1')"
            ),
            {"org": organization, "case_id": row.id, "outcome": outcome},
        )
        content_hash = hashlib.sha256(f"{reference}:{outcome}:{notice_kind}".encode()).hexdigest()
        connection.execute(
            text(
                "INSERT INTO screening_notices (organization_id, id, case_id, notice_kind, content_hash, delivery_state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :case_id, :notice_kind, :content_hash, 'queued')"
            ),
            {"org": organization, "case_id": row.id, "notice_kind": notice_kind, "content_hash": content_hash},
        )
        connection.execute(
            text("UPDATE screening_cases SET state = 'decided', version = version + 1 WHERE id = :case_id"),
            {"case_id": row.id},
        )
    return {"outcome": outcome, "notice_kind": notice_kind, "human_confirmed": True}


def open_dispute(settings: Settings, actor, organization, reference: str, dispute_kind: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text("SELECT id FROM screening_cases WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "not_found", "The screening case was not found.", False)
        connection.execute(
            text(
                "INSERT INTO screening_disputes (organization_id, id, case_id, dispute_kind, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :case_id, :kind, 'submitted')"
            ),
            {"org": organization, "case_id": row.id, "kind": dispute_kind[:80]},
        )
    return {"state": "submitted"}


def create_handoff(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text(
                "SELECT screening_case.id, decision.outcome FROM screening_cases screening_case "
                "JOIN screening_decisions decision ON decision.organization_id = screening_case.organization_id "
                "AND decision.case_id = screening_case.id WHERE screening_case.public_reference = :reference"
            ),
            {"reference": reference},
        ).first()
        if row is None or row.outcome != "approved":
            raise CommandError(409, "conflict", "Only an approved decision can be handed to the next phase.", False)
        package_hash = hashlib.sha256(f"{reference}:approved".encode()).hexdigest()
        connection.execute(
            text(
                "INSERT INTO screening_handoffs (organization_id, id, case_id, package_hash) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :case_id, :package_hash)"
            ),
            {"org": organization, "case_id": row.id, "package_hash": package_hash},
        )
    return {"handed_off": True, "package_hash": package_hash}

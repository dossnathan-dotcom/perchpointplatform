"""Phase 14 lease preparation. A person approves the package. A fake signature does not move money."""
from __future__ import annotations

import hashlib
import hmac
import json
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
        status = 409 if row["code"] in {"conflict", "incomplete"} else 400
        raise CommandError(status, row["code"], "The lease request could not be accepted.", False)
    return row


def open_deal(settings: Settings, actor, organization, screening_reference: str, idempotency_key: str) -> dict:
    token = secrets.token_urlsafe(32)
    fingerprint = hashlib.sha256(f"{screening_reference}:{organization}".encode()).hexdigest()
    reference = f"lease-{uuid4().hex[:16]}"
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        existing = connection.execute(
            text("SELECT fingerprint, public_reference FROM lease_intake_keys WHERE idempotency_key = :key"),
            {"key": idempotency_key},
        ).first()
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise CommandError(409, "conflict", "The lease request could not be accepted.", False)
            return {"accepted": True, "reference": existing.public_reference, "replayed": True, "state": "reserved"}
        row = connection.execute(
            text(
                "SELECT screening_case.id FROM screening_cases screening_case "
                "JOIN screening_decisions decision ON decision.organization_id = screening_case.organization_id "
                "AND decision.case_id = screening_case.id AND decision.outcome = 'approved' "
                "JOIN screening_handoffs handoff ON handoff.organization_id = screening_case.organization_id "
                "AND handoff.case_id = screening_case.id "
                "WHERE screening_case.public_reference = :reference"
            ),
            {"reference": screening_reference},
        ).first()
        if row is None:
            raise CommandError(409, "conflict", "Only an approved handoff can start a lease.", False)
        active = connection.execute(
            text("SELECT public_reference FROM lease_deals WHERE case_id = :case_id AND state <> 'canceled'"),
            {"case_id": row.id},
        ).first()
        if active is not None:
            return {"accepted": True, "reference": active.public_reference, "replayed": True, "state": "reserved"}
        package_hash = hashlib.sha256(f"{screening_reference}:lease".encode()).hexdigest()
        deal_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO lease_deals (organization_id, id, case_id, public_reference, state, package_hash, amount_minor) "
                "VALUES (CAST(:org AS uuid), :deal_id, :case_id, :reference, 'reserved', :package_hash, 140000)"
            ),
            {"org": organization, "deal_id": deal_id, "case_id": row.id, "reference": reference, "package_hash": package_hash},
        )
        connection.execute(
            text(
                "INSERT INTO lease_capabilities (organization_id, token_hash, deal_id, expires_at) "
                "VALUES (CAST(:org AS uuid), :token_hash, :deal_id, now() + interval '2 days')"
            ),
            {"org": organization, "token_hash": _hash(token), "deal_id": deal_id},
        )
        connection.execute(
            text(
                "INSERT INTO lease_intake_keys (organization_id, idempotency_key, fingerprint, public_reference) "
                "VALUES (CAST(:org AS uuid), :key, :fingerprint, :reference)"
            ),
            {"org": organization, "key": idempotency_key, "fingerprint": fingerprint, "reference": reference},
        )
        connection.execute(
            text(
                "INSERT INTO deposit_obligations (organization_id, id, deal_id, amount_minor, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :deal_id, 140000, 'due')"
            ),
            {"org": organization, "deal_id": deal_id},
        )
    return {"accepted": True, "reference": reference, "replayed": False, "state": "reserved", "capability": token}


def approve_package(settings: Settings, actor, organization, reference: str, human_confirmed: bool) -> dict:
    if not human_confirmed:
        raise CommandError(400, "rejected", "The lease request could not be accepted.", False)
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text("SELECT id, state, package_hash FROM lease_deals WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "not_found", "The lease was not found.", False)
        if row.state != "reserved":
            raise CommandError(409, "conflict", "The lease is not ready for approval.", False)
        connection.execute(
            text(
                "INSERT INTO lease_approvals (organization_id, id, deal_id, package_hash, human_confirmed) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :deal_id, :package_hash, true)"
            ),
            {"org": organization, "deal_id": row.id, "package_hash": row.package_hash},
        )
        connection.execute(
            text(
                "INSERT INTO lease_packages (organization_id, id, deal_id, content_hash, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :deal_id, :package_hash, 'rendered')"
            ),
            {"org": organization, "deal_id": row.id, "package_hash": row.package_hash},
        )
        connection.execute(
            text("UPDATE lease_deals SET state = 'approved', version = version + 1 WHERE id = :deal_id"),
            {"deal_id": row.id},
        )
    return {"state": "approved", "human_confirmed": True, "package_hash": row.package_hash}


def place_signature(settings: Settings, capability: str, idempotency_key: str) -> dict:
    fingerprint = hashlib.sha256(f"{_hash(capability)}:sign".encode()).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.place_lease_signature(CAST(:token_hash AS text), CAST(:key AS text), CAST(:fingerprint AS text))",
            {"token_hash": _hash(capability), "key": idempotency_key, "fingerprint": fingerprint},
        )
    return {"accepted": True, "reference": row["reference"], "replayed": row["replayed"], "state": "signing"}


def apply_signature(settings: Settings, capability: str, body: bytes, signature: str) -> dict:
    expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        raise CommandError(400, "rejected", "The lease request could not be accepted.", False)
    payload = json.loads(body.decode())
    if payload.get("provider"):
        raise CommandError(400, "rejected", "The lease request could not be accepted.", False)
    event_hash = hashlib.sha256(capability.encode() + b"\n" + body).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.apply_lease_signature(CAST(:token_hash AS text), CAST(:event_hash AS text))",
            {"token_hash": _hash(capability), "event_hash": event_hash},
        )
    return {"accepted": True, "replayed": row["replayed"], "state": "executed"}


def satisfy_deposit(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text(
                "UPDATE deposit_obligations SET state = 'satisfied' "
                "WHERE deal_id = (SELECT id FROM lease_deals WHERE public_reference = :reference) "
                "AND state = 'due' RETURNING state"
            ),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(409, "conflict", "The deposit obligation is not open.", False)
    return {"state": "satisfied", "ledger_posted": False}


def activate_resident(settings: Settings, actor, organization, reference: str, idempotency_key: str) -> dict:
    fingerprint = hashlib.sha256(f"{reference}:activate".encode()).hexdigest()
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        existing = connection.execute(
            text("SELECT fingerprint, public_reference FROM lease_intake_keys WHERE idempotency_key = :key"),
            {"key": idempotency_key},
        ).first()
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise CommandError(409, "conflict", "The lease request could not be accepted.", False)
            return {"accepted": True, "replayed": True, "state": "activated"}
        row = connection.execute(
            text("SELECT id, state, package_hash FROM lease_deals WHERE public_reference = :reference FOR UPDATE"),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "not_found", "The lease was not found.", False)
        if row.state != "executed":
            raise CommandError(409, "conflict", "The lease is not executed.", False)
        deposit = connection.execute(
            text("SELECT state FROM deposit_obligations WHERE deal_id = :deal_id"),
            {"deal_id": row.id},
        ).scalar()
        if deposit != "satisfied":
            raise CommandError(409, "conflict", "The deposit obligation is not satisfied.", False)
        manifest = hashlib.sha256(f"{reference}:{row.package_hash}".encode()).hexdigest()
        try:
            connection.execute(
                text(
                    "INSERT INTO lease_activations (organization_id, id, deal_id, manifest_hash) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :deal_id, :manifest)"
                ),
                {"org": organization, "deal_id": row.id, "manifest": manifest},
            )
            connection.execute(
                text(
                    "INSERT INTO resident_households (organization_id, id, deal_id, state) "
                    "VALUES (CAST(:org AS uuid), gen_random_uuid(), :deal_id, 'active')"
                ),
                {"org": organization, "deal_id": row.id},
            )
        except IntegrityError as exc:
            raise CommandError(409, "conflict", "The lease is already activated.", False) from exc
        connection.execute(
            text("UPDATE lease_deals SET state = 'activated', version = version + 1 WHERE id = :deal_id"),
            {"deal_id": row.id},
        )
        connection.execute(
            text(
                "INSERT INTO lease_intake_keys (organization_id, idempotency_key, fingerprint, public_reference) "
                "VALUES (CAST(:org AS uuid), :key, :fingerprint, :reference)"
            ),
            {"org": organization, "key": idempotency_key, "fingerprint": fingerprint, "reference": reference},
        )
    return {"accepted": True, "replayed": False, "state": "activated", "manifest_hash": manifest}


def reject_payment() -> None:
    raise CommandError(400, "rejected", "The lease request could not be accepted.", False)

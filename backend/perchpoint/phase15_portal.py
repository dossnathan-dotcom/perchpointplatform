"""Phase 15 resident portal. Activation opens access. Later domains stay unactivated."""
from __future__ import annotations

import hashlib
import secrets
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .db import runtime_transaction
from .settings import Settings

SAMPLE_MARKER = "SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION"
SAMPLE_BODY = (
    f"{SAMPLE_MARKER}\n"
    "Fictional parties: Casey Synthetic and Example Homes. "
    "Fictional premises: 100 Example Court. "
    "Sample monthly figure 140000 minor units. "
    "This artifact is not for execution and is not legal advice."
)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _require(connection, capability: str) -> None:
    allowed = connection.execute(
        text("SELECT perchpoint.has_capability(:capability)"),
        {"capability": capability},
    ).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _call(connection, statement: str, params: dict) -> dict:
    row = connection.execute(text(statement), params).scalar_one()
    if not row["accepted"]:
        status = 409 if row["code"] == "conflict" else 400
        raise CommandError(status, row["code"], "The portal request could not be accepted.", False)
    return row


def open_portal(settings: Settings, actor, organization, reference: str, idempotency_key: str) -> dict:
    token = secrets.token_urlsafe(32)
    fingerprint = hashlib.sha256(f"{reference}:portal".encode()).hexdigest()
    public_reference = f"portal-{uuid4().hex[:16]}"
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        existing = connection.execute(
            text("SELECT fingerprint, public_reference FROM portal_intake_keys WHERE idempotency_key = :key"),
            {"key": idempotency_key},
        ).first()
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise CommandError(409, "conflict", "The portal request could not be accepted.", False)
            return {"accepted": True, "reference": existing.public_reference, "replayed": True, "state": "pending"}
        deal = connection.execute(
            text("SELECT id, state FROM lease_deals WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if deal is None or deal.state != "activated":
            raise CommandError(409, "conflict", "Only an activated lease can open a portal.", False)
        activation = connection.execute(
            text("SELECT id FROM lease_activations WHERE deal_id = :deal_id"),
            {"deal_id": deal.id},
        ).first()
        household = connection.execute(
            text("SELECT id FROM resident_households WHERE deal_id = :deal_id AND state = 'active'"),
            {"deal_id": deal.id},
        ).first()
        if activation is None or household is None:
            raise CommandError(409, "conflict", "Only an activated lease can open a portal.", False)
        membership_id = uuid4()
        document_id = uuid4()
        content_hash = hashlib.sha256(SAMPLE_BODY.encode()).hexdigest()
        try:
            connection.execute(
                text(
                    "INSERT INTO portal_memberships "
                    "(organization_id, id, deal_id, public_reference, role_name, state, person_label) "
                    "VALUES (CAST(:org AS uuid), :membership_id, :deal_id, :reference, 'leaseholder', 'pending', 'Casey Synthetic')"
                ),
                {
                    "org": organization,
                    "membership_id": membership_id,
                    "deal_id": deal.id,
                    "reference": public_reference,
                },
            )
        except IntegrityError as exc:
            raise CommandError(409, "conflict", "The portal request could not be accepted.", False) from exc
        connection.execute(
            text(
                "INSERT INTO portal_invitations "
                "(organization_id, id, membership_id, token_hash, purpose, state, expires_at) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :membership_id, :token_hash, "
                "'household_access', 'issued', now() + interval '2 days')"
            ),
            {"org": organization, "membership_id": membership_id, "token_hash": _hash(token)},
        )
        connection.execute(
            text(
                "INSERT INTO portal_documents "
                "(organization_id, id, membership_id, artifact_code, content_hash, body, sample_marker) "
                "VALUES (CAST(:org AS uuid), :document_id, :membership_id, 'sample_lease', :content_hash, :body, :marker)"
            ),
            {
                "org": organization,
                "document_id": document_id,
                "membership_id": membership_id,
                "content_hash": content_hash,
                "body": SAMPLE_BODY,
                "marker": SAMPLE_MARKER,
            },
        )
        connection.execute(
            text(
                "INSERT INTO portal_entitlements (organization_id, id, membership_id, document_id, state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :membership_id, :document_id, 'current')"
            ),
            {"org": organization, "membership_id": membership_id, "document_id": document_id},
        )
        connection.execute(
            text(
                "INSERT INTO portal_activity (organization_id, id, membership_id, action_code, safe_label) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :membership_id, 'portal.opened', 'Household access prepared')"
            ),
            {"org": organization, "membership_id": membership_id},
        )
        connection.execute(
            text(
                "INSERT INTO portal_outbox (organization_id, id, membership_id, event_code, delivery_state) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :membership_id, 'invitation.queued', 'queued')"
            ),
            {"org": organization, "membership_id": membership_id},
        )
        connection.execute(
            text(
                "INSERT INTO portal_intake_keys (organization_id, idempotency_key, fingerprint, public_reference) "
                "VALUES (CAST(:org AS uuid), :key, :fingerprint, :reference)"
            ),
            {"org": organization, "key": idempotency_key, "fingerprint": fingerprint, "reference": public_reference},
        )
    return {
        "accepted": True,
        "reference": public_reference,
        "replayed": False,
        "state": "pending",
        "capability": token,
    }


def accept_invitation(settings: Settings, capability: str, idempotency_key: str) -> dict:
    fingerprint = hashlib.sha256(f"{_hash(capability)}:accept".encode()).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = _call(
            connection,
            "SELECT perchpoint.accept_portal_invitation(CAST(:token_hash AS text), CAST(:key AS text), CAST(:fingerprint AS text))",
            {"token_hash": _hash(capability), "key": idempotency_key, "fingerprint": fingerprint},
        )
    return {"accepted": True, "replayed": row["replayed"], "state": row["state"]}


def read_home(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text(
                "SELECT membership.state, membership.role_name, document.sample_marker "
                "FROM portal_memberships membership "
                "JOIN portal_documents document ON document.membership_id = membership.id "
                "WHERE membership.public_reference = :reference AND document.superseded = false"
            ),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "not_found", "The household was not found.", False)
    return {
        "state": row.state,
        "role_name": row.role_name,
        "sample_marker": row.sample_marker,
        "ledger_posted": False,
        "previews": [
            {"kind": "balance", "demo_preview": True, "owning_phase": 16, "authoritative": False},
            {"kind": "payment", "demo_preview": True, "owning_phase": 17, "authoritative": False},
            {"kind": "maintenance", "demo_preview": True, "owning_phase": 20, "authoritative": False},
            {"kind": "message", "demo_preview": True, "owning_phase": 23, "authoritative": False},
        ],
    }


def download_document(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text(
                "SELECT document.body, document.sample_marker, entitlement.state AS entitlement_state, "
                "membership.state AS membership_state "
                "FROM portal_memberships membership "
                "JOIN portal_entitlements entitlement ON entitlement.membership_id = membership.id "
                "JOIN portal_documents document ON document.id = entitlement.document_id "
                "WHERE membership.public_reference = :reference AND document.superseded = false"
            ),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "not_found", "The document was not found.", False)
        if row.membership_state != "active" or row.entitlement_state != "current":
            raise CommandError(409, "conflict", "The document is not currently entitled.", False)
        connection.execute(
            text(
                "INSERT INTO portal_activity (organization_id, id, membership_id, action_code, safe_label) "
                "SELECT organization_id, gen_random_uuid(), id, 'document.downloaded', 'Sample lease downloaded' "
                "FROM portal_memberships WHERE public_reference = :reference"
            ),
            {"reference": reference},
        )
    return {
        "body": row.body,
        "sample_marker": row.sample_marker,
        "cache_control": "no-store",
        "authoritative_signed_bytes": False,
    }


def set_preference(settings: Settings, actor, organization, reference: str, channel: str, quiet_hours: bool) -> dict:
    if channel not in {"portal", "email"}:
        raise CommandError(400, "rejected", "The portal request could not be accepted.", False)
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        membership = connection.execute(
            text("SELECT id, state FROM portal_memberships WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if membership is None or membership.state != "active":
            raise CommandError(409, "conflict", "The household is not active.", False)
        version = connection.execute(
            text("SELECT coalesce(max(version), 0) + 1 FROM portal_preferences WHERE membership_id = :membership_id"),
            {"membership_id": membership.id},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO portal_preferences (organization_id, id, membership_id, version, channel, quiet_hours) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :membership_id, :version, :channel, :quiet_hours)"
            ),
            {
                "org": organization,
                "membership_id": membership.id,
                "version": version,
                "channel": channel,
                "quiet_hours": quiet_hours,
            },
        )
    return {"version": version, "channel": channel, "quiet_hours": quiet_hours}


def submit_request(settings: Settings, actor, organization, reference: str, request_kind: str, requested_delta: str) -> dict:
    if request_kind not in {"profile", "access", "accommodation"} or not requested_delta:
        raise CommandError(400, "rejected", "The portal request could not be accepted.", False)
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        membership = connection.execute(
            text(
                "SELECT membership.id, membership.state AS membership_state, lease_deal.state AS lease_state "
                "FROM portal_memberships membership "
                "JOIN lease_deals lease_deal ON lease_deal.id = membership.deal_id "
                "WHERE membership.public_reference = :reference"
            ),
            {"reference": reference},
        ).first()
        if membership is None or membership.membership_state != "active":
            raise CommandError(409, "conflict", "The household is not active.", False)
        connection.execute(
            text(
                "INSERT INTO portal_requests "
                "(organization_id, id, membership_id, request_kind, state, requested_delta, sensitive) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :membership_id, :request_kind, 'submitted', :requested_delta, :sensitive)"
            ),
            {
                "org": organization,
                "membership_id": membership.id,
                "request_kind": request_kind,
                "requested_delta": requested_delta,
                "sensitive": request_kind == "accommodation",
            },
        )
        lease_state = membership.lease_state
    return {"state": "submitted", "lease_state": lease_state, "canonical_changed": False}


def revoke_membership(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text(
                "UPDATE portal_memberships SET state = 'revoked', version = version + 1 "
                "WHERE public_reference = :reference AND state = 'active' RETURNING id"
            ),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(409, "conflict", "The household is not active.", False)
        connection.execute(
            text("UPDATE portal_invitations SET state = 'revoked' WHERE membership_id = :membership_id"),
            {"membership_id": row.id},
        )
        connection.execute(
            text("UPDATE portal_entitlements SET state = 'revoked' WHERE membership_id = :membership_id"),
            {"membership_id": row.id},
        )
    return {"state": "revoked"}


def publish_config(settings: Settings, actor, organization, family_code: str, clause_code: str, human_confirmed: bool) -> dict:
    if not human_confirmed or not family_code or not clause_code or clause_code == "overlap":
        raise CommandError(400, "rejected", "The configuration could not be published.", False)
    content_hash = hashlib.sha256(f"{family_code}:{clause_code}".encode()).hexdigest()
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        version = connection.execute(
            text("SELECT coalesce(max(version), 0) + 1 FROM portal_config_versions WHERE family_code = :family_code"),
            {"family_code": family_code},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO portal_config_versions "
                "(organization_id, id, family_code, version, state, content_hash, clause_code, human_confirmed) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :family_code, :version, 'published', :content_hash, :clause_code, true)"
            ),
            {
                "org": organization,
                "family_code": family_code,
                "version": version,
                "content_hash": content_hash,
                "clause_code": clause_code,
            },
        )
    return {"state": "published", "version": version, "content_hash": content_hash, "edited_in_place": False}


def dry_run_manifest(settings: Settings, actor, organization, payload: dict) -> dict:
    if any(key in payload for key in ("secret", "credential", "password", "token")):
        raise CommandError(400, "rejected", "The portal request could not be accepted.", False)
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        connection.execute(
            text(
                "INSERT INTO portal_manifest_runs "
                "(organization_id, id, manifest_version, dry_run, real_values_activated) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), 1, true, false)"
            ),
            {"org": organization},
        )
    return {"dry_run": True, "real_values_activated": False, "synthetic": True}


def reject_later_domain() -> None:
    raise CommandError(400, "rejected", "The portal request could not be accepted.", False)

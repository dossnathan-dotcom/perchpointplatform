"""Server-custodied sessions. The browser receives an opaque cookie, not a provider refresh token."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import bcrypt
from cryptography.fernet import Fernet
from sqlalchemy import text

from .db import runtime_transaction
from .phase6_policy import OWNER_RESERVED
from .settings import Settings

COOKIE = "pp_session"
CSRF_HEADER = "x-perchpoint-csrf"


def _hash(value: str) -> str:
    key = os.environ.get("PHASE6_SESSION_KEY", "local-only-not-production-session-key").encode()
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def _limits(role_name: str) -> tuple[timedelta, timedelta]:
    if role_name in {"owner", "platform_admin"}:
        return timedelta(minutes=15), timedelta(hours=8)
    if role_name in {"applicant", "resident"}:
        return timedelta(days=30), timedelta(days=30)
    return timedelta(hours=1), timedelta(hours=24)


def open_session(
    settings: Settings,
    account: UUID,
    organization: UUID,
    role_name: str,
    subject: str,
    assurance: str = "aal1",
    *,
    refresh_token: str | None = None,
    provider_session_id: str | None = None,
) -> dict:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    idle, absolute = _limits(role_name)
    now = datetime.now(timezone.utc)
    workforce = role_name not in {"applicant", "resident", "household_adult", "guarantor"}
    limit = 3 if workforce else 5
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        existing = connection.execute(
            text(
                """
                SELECT s.id FROM identity_sessions s
                JOIN identity_accounts a ON a.id = s.identity_id
                WHERE a.account_id = :account AND s.revoked_at IS NULL AND s.absolute_expires_at > now()
                ORDER BY s.created_at ASC
                """
            ),
            {"account": account},
        ).scalars().all()
        overflow = list(existing)[0 : max(0, len(existing) + 1 - limit)]
        for old in overflow:
            connection.execute(text("UPDATE identity_sessions SET revoked_at = now(), revoke_reason = 'concurrent_limit' WHERE id = :id"), {"id": old})
        session_id = connection.execute(
            text(
                """
                SELECT perchpoint.record_provider_session(
                  :account, :subject, :org, :token_hash, :csrf_hash, :assurance, :device,
                  :idle, :absolute, :idle_seconds, :provider_session, :refresh_ciphertext
                )
                """
            ),
            {
                "account": account,
                "subject": subject,
                "org": organization,
                "token_hash": _hash(token),
                "csrf_hash": _hash(csrf),
                "assurance": assurance,
                "device": "synthetic-browser",
                "idle": now + idle,
                "absolute": now + absolute,
                "idle_seconds": int(idle.total_seconds()),
                "provider_session": provider_session_id,
                "refresh_ciphertext": None if refresh_token is None else _fernet().encrypt(refresh_token.encode()).decode(),
            },
        ).scalar()
    return {"session_id": str(session_id), "token": token, "csrf": csrf, "assurance": assurance}


def resolve(settings: Settings, token: str | None) -> dict | None:
    if not token:
        return None
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(text("SELECT * FROM perchpoint.resolve_session(:token)"), {"token": _hash(token)}).mappings().first()
    if not row or row["revoked_at"] is not None:
        return None
    now = datetime.now(timezone.utc)
    if row["idle_expires_at"] < now or row["absolute_expires_at"] < now:
        return None
    return {
        "id": row["account_id"],
        "organization_id": row["organization_id"],
        "session_id": row["session_id"],
        "assurance": row["assurance"],
        "reauthenticated_at": row["reauthenticated_at"],
        "csrf_hash": row["csrf_hash"],
        "status": row["status"],
        "refresh_ciphertext": row["refresh_ciphertext"],
    }


def refresh_token_for(session: dict) -> str | None:
    raw = session.get("refresh_ciphertext")
    if not raw:
        return None
    return _fernet().decrypt(str(raw).encode()).decode()


def csrf_ok(session: dict, presented: str | None) -> bool:
    if not presented:
        return False
    return secrets.compare_digest(session["csrf_hash"], _hash(presented))


def _fernet() -> Fernet:
    raw = os.environ.get("PHASE6_SESSION_KEY", "local-only-not-production-session-key")
    key = base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest())
    return Fernet(key)


def create_invitation(settings: Settings, actor: UUID, organization: UUID, email: str, role_name: str, purpose: str, *, staff: bool) -> dict:
    token = secrets.token_urlsafe(32)
    hours = 24 if staff else 72
    invitation_id = uuid4()
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        connection.execute(
            text(
                """
                INSERT INTO identity_invitations (
                  organization_id, id, email, token_hash, role_name, purpose, inviter_id, expires_at
                ) VALUES (
                  :org, :id, :email, :token_hash, :role, :purpose, :inviter, now() + make_interval(hours => :hours)
                )
                """
            ),
            {
                "org": organization,
                "id": invitation_id,
                "email": email,
                "token_hash": _hash(token),
                "role": role_name,
                "purpose": purpose,
                "inviter": actor,
                "hours": hours,
            },
        )
    return {"invitation_id": str(invitation_id), "token": token, "expires_in_hours": hours}


def accept_invitation(settings: Settings, token: str) -> bool:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        return bool(connection.execute(text("SELECT perchpoint.accept_invitation(:token)"), {"token": _hash(token)}).scalar())


def remember_factor(settings: Settings, account: UUID, organization: UUID, provider_factor_id: str) -> None:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        identity = connection.execute(text("SELECT id FROM identity_accounts WHERE account_id = :account"), {"account": account}).scalar()
        connection.execute(
            text(
                """
                INSERT INTO identity_factors (id, identity_id, kind, provider_factor_id)
                VALUES (:id, :identity, 'totp', :provider_factor)
                """
            ),
            {"id": uuid4(), "identity": identity, "provider_factor": provider_factor_id},
        )


def mark_factor_confirmed(settings: Settings, account: UUID, organization: UUID, provider_factor_id: str) -> None:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        connection.execute(
            text("UPDATE identity_factors SET confirmed_at = now() WHERE provider_factor_id = :factor AND confirmed_at IS NULL"),
            {"factor": provider_factor_id},
        )
        connection.execute(text("UPDATE identity_accounts SET assurance = 'aal2' WHERE account_id = :account"), {"account": account})


def issue_recovery_codes(settings: Settings, account: UUID, organization: UUID) -> list[str]:
    codes = [secrets.token_hex(8) for _ in range(10)]
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        identity = connection.execute(text("SELECT id FROM identity_accounts WHERE account_id = :account"), {"account": account}).scalar()
        connection.execute(text("DELETE FROM identity_recovery_codes WHERE identity_id = :identity AND used_at IS NULL"), {"identity": identity})
        for code in codes:
            connection.execute(
                text("INSERT INTO identity_recovery_codes (id, identity_id, code_hash) VALUES (:id, :identity, :code_hash)"),
                {"id": uuid4(), "identity": identity, "code_hash": bcrypt.hashpw(code.encode(), bcrypt.gensalt()).decode()},
            )
    return codes


def create_delegation(
    settings: Settings,
    grantor: UUID,
    organization: UUID,
    grantee: UUID,
    capability: str,
    reason: str,
    *,
    days: int,
    amount_ceiling_minor: int | None = None,
) -> str:
    if grantor == grantee:
        raise ValueError("self_delegation")
    if days < 1 or days > 30:
        raise ValueError("delegation_window")
    if capability in OWNER_RESERVED:
        raise ValueError("owner_reserved")
    delegation_id = uuid4()
    with runtime_transaction(settings, grantor, organization, uuid4()) as connection:
        connection.execute(
            text(
                """
                INSERT INTO delegations (
                  organization_id, id, grantor_id, grantee_id, capability, amount_ceiling_minor, ends_at, status, reason
                ) VALUES (
                  :org, :id, :grantor, :grantee, :capability, :ceiling, now() + make_interval(days => :days), 'active', :reason
                )
                """
            ),
            {
                "org": organization,
                "id": delegation_id,
                "grantor": grantor,
                "grantee": grantee,
                "capability": capability,
                "ceiling": amount_ceiling_minor,
                "days": days,
                "reason": reason,
            },
        )
    return str(delegation_id)


def expire_invitation(settings: Settings, actor: UUID, organization: UUID, invitation_id: UUID) -> None:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE identity_invitations
                SET created_at = now() - interval '2 minutes',
                    expires_at = now() - interval '1 minute'
                WHERE id = :id AND organization_id = :org AND inviter_id = :actor AND accepted_at IS NULL AND revoked_at IS NULL
                """
            ),
            {"id": invitation_id, "org": organization, "actor": actor},
        ).rowcount
    if not updated:
        raise ValueError("invitation_invalid")


def revoke_invitation(settings: Settings, actor: UUID, organization: UUID, invitation_id: UUID) -> None:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE identity_invitations
                SET revoked_at = now()
                WHERE id = :id AND organization_id = :org AND inviter_id = :actor AND accepted_at IS NULL AND revoked_at IS NULL
                """
            ),
            {"id": invitation_id, "org": organization, "actor": actor},
        ).rowcount
    if not updated:
        raise ValueError("invitation_invalid")


def revoke_delegation(settings: Settings, actor: UUID, organization: UUID, delegation_id: UUID) -> None:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE delegations
                SET status = 'revoked', revoked_at = now()
                WHERE id = :id AND organization_id = :org AND grantor_id = :actor AND status = 'active'
                """
            ),
            {"id": delegation_id, "org": organization, "actor": actor},
        ).rowcount
    if not updated:
        raise ValueError("delegation_invalid")


def expire_delegation(settings: Settings, actor: UUID, organization: UUID, delegation_id: UUID) -> None:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE delegations
                SET status = 'expired', ends_at = now() - interval '1 minute'
                WHERE id = :id AND organization_id = :org AND grantor_id = :actor AND status = 'active'
                """
            ),
            {"id": delegation_id, "org": organization, "actor": actor},
        ).rowcount
    if not updated:
        raise ValueError("delegation_invalid")


def list_sessions(settings: Settings, account: UUID, organization: UUID) -> list[dict]:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT s.id, s.device_label, s.created_at, s.last_seen_at, s.revoked_at IS NOT NULL AS revoked
                FROM identity_sessions s
                JOIN identity_accounts a ON a.id = s.identity_id
                WHERE a.account_id = :account
                ORDER BY s.created_at DESC
                """
            ),
            {"account": account},
        ).mappings().all()
    return [{"id": str(row["id"]), "device_label": row["device_label"], "revoked": row["revoked"]} for row in rows]


def revoke_others(settings: Settings, account: UUID, organization: UUID, session_id: UUID) -> int:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        result = connection.execute(
            text(
                """
                UPDATE identity_sessions SET revoked_at = now(), revoke_reason = 'sign_out_others'
                WHERE revoked_at IS NULL AND id <> :id
                  AND identity_id IN (SELECT id FROM identity_accounts WHERE account_id = :account)
                """
            ),
            {"id": session_id, "account": account},
        )
    return result.rowcount or 0


def select_context(settings: Settings, account: UUID, organization: UUID, session_id: UUID, membership_id: UUID) -> dict:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        rows = connection.execute(text("SELECT * FROM perchpoint.list_memberships(:account)"), {"account": account}).mappings().all()
        match = next((row for row in rows if row["membership_id"] == membership_id), None)
        if match is None:
            raise ValueError("context_invalid")
        connection.execute(
            text("UPDATE identity_sessions SET organization_id = :org, context_membership = :membership WHERE id = :id"),
            {"org": match["organization_id"], "membership": membership_id, "id": session_id},
        )
    return {"organization_id": str(match["organization_id"]), "role_name": match["role_name"]}


def create_access_request(settings: Settings, requester: UUID, organization: UUID, capability: str, justification: str) -> str:
    request_id = uuid4()
    with runtime_transaction(settings, requester, organization, uuid4()) as connection:
        connection.execute(
            text(
                """
                INSERT INTO access_requests (organization_id, id, requester_id, capability, justification, status)
                VALUES (:org, :id, :requester, :capability, :justification, 'pending')
                """
            ),
            {"org": organization, "id": request_id, "requester": requester, "capability": capability, "justification": justification},
        )
    return str(request_id)


def decide_access_request(settings: Settings, approver: UUID, organization: UUID, request_id: UUID, approve: bool) -> None:
    with runtime_transaction(settings, approver, organization, uuid4()) as connection:
        row = connection.execute(
            text("SELECT requester_id FROM access_requests WHERE id = :id AND organization_id = :org AND status = 'pending'"),
            {"id": request_id, "org": organization},
        ).mappings().first()
        if row is None:
            raise ValueError("request_missing")
        if row["requester_id"] == approver:
            raise ValueError("self_approval")
        connection.execute(
            text("UPDATE access_requests SET status = :status, approver_id = :approver WHERE id = :id"),
            {"status": "approved" if approve else "denied", "approver": approver, "id": request_id},
        )


def issue_service_credential(settings: Settings, actor: UUID, organization: UUID, principal_id: UUID) -> str:
    secret = secrets.token_urlsafe(32)
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        principal = connection.execute(
            text("SELECT interactive FROM service_principals WHERE id = :id AND organization_id = :org AND status = 'active'"),
            {"id": principal_id, "org": organization},
        ).mappings().first()
        if principal is None or principal["interactive"]:
            raise ValueError("principal_invalid")
        connection.execute(
            text(
                """
                INSERT INTO service_credentials (organization_id, id, principal_id, verifier_hash, expires_at)
                VALUES (:org, :id, :principal, :verifier, now() + interval '1 day')
                """
            ),
            {"org": organization, "id": uuid4(), "principal": principal_id, "verifier": _hash(secret)},
        )
    return secret


def open_privileged_recovery(settings: Settings, initiator: UUID, organization: UUID, subject: UUID, evidence: str, approver: UUID | None) -> str:
    if initiator == subject or approver == subject:
        raise ValueError("self_recovery")
    recovery_id = uuid4()
    with runtime_transaction(settings, initiator, organization, uuid4()) as connection:
        connection.execute(
            text(
                """
                INSERT INTO privileged_recoveries (
                  organization_id, id, subject_account, initiator_account, approver_account, status, not_before, evidence_note
                ) VALUES (
                  :org, :id, :subject, :initiator, :approver, 'waiting', now() + interval '15 minutes', :evidence
                )
                """
            ),
            {"org": organization, "id": recovery_id, "subject": subject, "initiator": initiator, "approver": approver, "evidence": evidence},
        )
    return str(recovery_id)


def revoke(settings: Settings, account: UUID, organization: UUID, session_id: UUID, reason: str) -> None:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        connection.execute(
            text("UPDATE identity_sessions SET revoked_at = now(), revoke_reason = :reason WHERE id = :id AND revoked_at IS NULL"),
            {"id": session_id, "reason": reason},
        )

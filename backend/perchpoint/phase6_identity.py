"""Server-custodied sessions. The browser receives an opaque cookie, not a provider refresh token."""
from __future__ import annotations

import base64
import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import bcrypt
from cryptography.fernet import Fernet
from sqlalchemy import text

from .db import runtime_transaction
from .phase6_policy import totp_matches
from .settings import Settings

COOKIE = "pp_session"
CSRF_HEADER = "x-perchpoint-csrf"


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _limits(role_name: str) -> tuple[timedelta, timedelta]:
    if role_name in {"owner", "platform_admin"}:
        return timedelta(minutes=15), timedelta(hours=8)
    if role_name in {"applicant", "resident"}:
        return timedelta(days=30), timedelta(days=30)
    return timedelta(hours=1), timedelta(hours=24)


def open_session(settings: Settings, account: UUID, organization: UUID, role_name: str, subject: str, assurance: str = "aal1") -> dict:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    idle, absolute = _limits(role_name)
    now = datetime.now(timezone.utc)
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        session_id = connection.execute(
            text(
                """
                SELECT perchpoint.record_session(
                  :account, :subject, :org, :token_hash, :csrf_hash, :assurance, :device, :idle, :absolute
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
    }


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


def enroll_totp(settings: Settings, account: UUID, organization: UUID) -> dict:
    secret = secrets.token_bytes(20)
    factor_id = uuid4()
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        identity = connection.execute(text("SELECT id FROM identity_accounts WHERE account_id = :account"), {"account": account}).scalar()
        connection.execute(
            text(
                """
                INSERT INTO identity_factors (id, identity_id, kind, secret_ciphertext)
                VALUES (:id, :identity, 'totp', :secret)
                """
            ),
            {"id": factor_id, "identity": identity, "secret": _fernet().encrypt(secret).decode()},
        )
    encoded = base64.b32encode(secret).decode().rstrip("=")
    return {"factor_id": str(factor_id), "secret": encoded, "otpauth": f"otpauth://totp/PerchPoint:{account}?secret={encoded}&issuer=PerchPoint"}


def confirm_totp(settings: Settings, account: UUID, organization: UUID, factor_id: UUID, code: str) -> bool:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        row = connection.execute(
            text("SELECT secret_ciphertext FROM identity_factors WHERE id = :id AND confirmed_at IS NULL AND removed_at IS NULL"),
            {"id": factor_id},
        ).scalar()
        if not row or not totp_matches(_fernet().decrypt(row.encode()), code):
            return False
        connection.execute(text("UPDATE identity_factors SET confirmed_at = now() WHERE id = :id"), {"id": factor_id})
        connection.execute(text("UPDATE identity_accounts SET assurance = 'aal2' WHERE account_id = :account"), {"account": account})
    return True


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


def revoke(settings: Settings, account: UUID, organization: UUID, session_id: UUID, reason: str) -> None:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        connection.execute(
            text("UPDATE identity_sessions SET revoked_at = now(), revoke_reason = :reason WHERE id = :id AND revoked_at IS NULL"),
            {"id": session_id, "reason": reason},
        )

"""Server-custodied sessions. The browser receives an opaque cookie, not a provider refresh token."""
from __future__ import annotations

import hashlib
import os
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

from sqlalchemy import text

from .db import runtime_transaction
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


def revoke(settings: Settings, account: UUID, organization: UUID, session_id: UUID, reason: str) -> None:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        connection.execute(
            text("UPDATE identity_sessions SET revoked_at = now(), revoke_reason = :reason WHERE id = :id AND revoked_at IS NULL"),
            {"id": session_id, "reason": reason},
        )

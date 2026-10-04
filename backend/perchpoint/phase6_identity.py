"""Server-custodied sessions. The browser receives an opaque cookie, not a provider refresh token."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import smtplib
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from uuid import UUID, uuid4

import bcrypt
from cryptography.fernet import Fernet
from sqlalchemy import text

from .db import runtime_transaction
from .phase6_policy import BUNDLES, OWNER_RESERVED
from .settings import Settings, configured_session_keys

COOKIE = "pp_session"
CSRF_HEADER = "x-perchpoint-csrf"


def _session_keys() -> list[str]:
    return configured_session_keys()


def _hash(value: str, key: str | None = None) -> str:
    material = (key or _session_keys()[0]).encode()
    return hmac.new(material, value.encode(), hashlib.sha256).hexdigest()


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
    membership_id: UUID | None = None,
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
                "refresh_ciphertext": None if refresh_token is None else _fernets()[0].encrypt(refresh_token.encode()).decode(),
            },
        ).scalar()
        connection.execute(
            text(
                """
                UPDATE identity_sessions
                SET refresh_family_id = :family,
                    refresh_generation = 0,
                    context_membership = :membership
                WHERE id = :session
                """
            ),
            {
                "family": uuid4(),
                "session": session_id,
                "membership": membership_id,
            },
        )
    return {"session_id": str(session_id), "token": token, "csrf": csrf, "assurance": assurance}


def resolve(settings: Settings, token: str | None) -> dict | None:
    if not token:
        return None
    row = None
    for key in _session_keys():
        with runtime_transaction(settings, None, None, uuid4()) as connection:
            row = connection.execute(
                text("SELECT * FROM perchpoint.resolve_session(:token)"),
                {"token": _hash(token, key)},
            ).mappings().first()
        if row:
            break
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
        "context_membership": row["context_membership"],
    }


def refresh_token_for(session: dict) -> str | None:
    raw = session.get("refresh_ciphertext")
    if not raw:
        return None
    for cipher in _fernets():
        try:
            return cipher.decrypt(str(raw).encode()).decode()
        except Exception:
            continue
    raise ValueError("provider_refresh_decryption_failed")


def replace_provider_refresh(
    settings: Settings,
    account: UUID,
    organization: UUID,
    session_id: UUID,
    refresh_token: str,
    provider_session_id: str | None,
) -> None:
    ciphertext = _fernets()[0].encrypt(refresh_token.encode()).decode()
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE identity_sessions
                SET refresh_ciphertext = :ciphertext,
                    provider_session_id = :provider_session,
                    refresh_generation = refresh_generation + 1
                WHERE id = :session
                  AND revoked_at IS NULL
                RETURNING id
                """
            ),
            {
                "ciphertext": ciphertext,
                "provider_session": provider_session_id,
                "session": session_id,
            },
        ).scalar()
    if updated is None:
        raise ValueError("session_inactive")


def record_provider_refresh_reuse(
    settings: Settings,
    account: UUID,
    organization: UUID,
    session_id: UUID,
) -> None:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        connection.execute(
            text(
                """
                UPDATE identity_sessions
                SET revoked_at = COALESCE(revoked_at, now()),
                    revoke_reason = CASE
                      WHEN revoked_at IS NULL THEN 'provider_refresh_reuse'
                      ELSE revoke_reason
                    END,
                    refresh_reuse_detected_at = CASE
                      WHEN id = :session THEN now()
                      ELSE refresh_reuse_detected_at
                    END
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                )
                """
            ),
            {"session": session_id, "account": account},
        )


def begin_email_change(
    settings: Settings,
    account: UUID,
    organization: UUID,
    new_email: str,
) -> dict:
    change_id = uuid4()
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        row = connection.execute(
            text(
                """
                SELECT identity.id AS identity_id, account.email
                FROM identity_accounts identity
                JOIN accounts account ON account.id = identity.account_id
                WHERE identity.account_id = :account
                """
            ),
            {"account": account},
        ).mappings().first()
        if row is None:
            raise ValueError("identity_missing")
        blocked = connection.execute(
            text(
                """
                SELECT 1
                FROM identity_contact_history
                WHERE identity_id = :identity
                  AND contact_kind = 'email'
                  AND (
                    status = 'pending'
                    OR cooldown_until > now()
                  )
                LIMIT 1
                """
            ),
            {"identity": row["identity_id"]},
        ).scalar()
        if blocked:
            raise ValueError("contact_change_cooldown")
        connection.execute(
            text(
                """
                INSERT INTO identity_contact_history (
                  organization_id, id, identity_id, contact_kind, previous_value,
                  proposed_value, status, cooldown_until
                ) VALUES (
                  :org, :id, :identity, 'email', :previous, :proposed, 'pending',
                  now() + interval '24 hours'
                )
                """
            ),
            {
                "org": organization,
                "id": change_id,
                "identity": row["identity_id"],
                "previous": row["email"],
                "proposed": new_email.lower(),
            },
        )
    return {"change_id": change_id, "previous_email": row["email"]}


def cancel_email_change(
    settings: Settings,
    account: UUID,
    organization: UUID,
    change_id: UUID,
) -> None:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        connection.execute(
            text(
                """
                UPDATE identity_contact_history
                SET status = 'cancelled'
                WHERE organization_id = :org
                  AND id = :id
                  AND status = 'pending'
                """
            ),
            {"org": organization, "id": change_id},
        )


def send_local_notice(email: str, subject: str, content: str) -> None:
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = "noreply@perchpoint.local"
    message["To"] = email
    message.set_content(content)
    host = os.environ.get("PHASE6_SMTP_HOST", "127.0.0.1")
    port = int(os.environ.get("PHASE6_SMTP_PORT", "1025"))
    with smtplib.SMTP(host, port, timeout=8) as smtp:
        smtp.send_message(message)


def csrf_ok(session: dict, presented: str | None) -> bool:
    if not presented:
        return False
    return any(secrets.compare_digest(session["csrf_hash"], _hash(presented, key)) for key in _session_keys())


def _fernets() -> list[Fernet]:
    return [
        Fernet(base64.urlsafe_b64encode(hashlib.sha256(raw.encode()).digest()))
        for raw in _session_keys()
    ]


def create_invitation(
    settings: Settings,
    actor: UUID,
    organization: UUID,
    email: str,
    role_name: str,
    purpose: str,
    *,
    staff: bool,
    relationship_type: str = "organization_membership",
    relationship_id: UUID | None = None,
    scope_payload: dict | None = None,
    approval_status: str = "approved",
) -> dict:
    if role_name not in BUNDLES:
        raise ValueError("invitation_role_invalid")
    internal_roles = {
        "owner",
        "platform_admin",
        "project_manager",
        "operations_manager",
        "leasing",
        "leasing_staff",
        "maintenance",
        "maintenance_coordinator",
        "accounting",
        "limited_approver",
    }
    staff = role_name in internal_roles
    token = secrets.token_urlsafe(32)
    hours = 24 if staff else 72
    invitation_id = uuid4()
    relationship_id = relationship_id or organization
    scope_payload = scope_payload or {"type": "organization", "resource_id": str(organization)}
    if approval_status not in {"pending", "approved"}:
        raise ValueError("invitation_approval_invalid")
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        connection.execute(
            text(
                """
                INSERT INTO identity_invitations (
                  organization_id, id, email, token_hash, role_name, purpose, inviter_id, expires_at,
                  relationship_type, relationship_id, scope_payload, approval_status
                ) VALUES (
                  :org, :id, :email, :token_hash, :role, :purpose, :inviter, now() + make_interval(hours => :hours),
                  :relationship_type, :relationship_id, CAST(:scope_payload AS jsonb), :approval_status
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
                "relationship_type": relationship_type,
                "relationship_id": relationship_id,
                "scope_payload": json.dumps(scope_payload, sort_keys=True),
                "approval_status": approval_status,
            },
        )
    message = EmailMessage()
    message["Subject"] = "Your synthetic PerchPoint invitation"
    message["From"] = "noreply@perchpoint.local"
    message["To"] = email
    message.set_content(
        "This message is synthetic and was delivered only to local Mailpit.\n\n"
        f"Accept: http://127.0.0.1:3000/invitation?token={token}\n"
        f"Purpose: {purpose}\n"
        f"Expires in: {hours} hours\n"
    )
    host = os.environ.get("PHASE6_SMTP_HOST", "127.0.0.1")
    port = int(os.environ.get("PHASE6_SMTP_PORT", "1025"))
    try:
        with smtplib.SMTP(host, port, timeout=8) as smtp:
            smtp.send_message(message)
    except OSError as exc:
        revoke_invitation(settings, actor, organization, invitation_id)
        raise RuntimeError("invitation_delivery_failed") from exc
    return {"invitation_id": str(invitation_id), "expires_in_hours": hours}


def accept_invitation(settings: Settings, token: str, email: str) -> bool:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        return bool(
            connection.execute(
                text("SELECT perchpoint.accept_invitation(:token, :email)"),
                {"token": _hash(token), "email": email},
            ).scalar()
        )


def activate_invitation(
    settings: Settings,
    token: str,
    email: str,
    provider_subject: str,
) -> dict | None:
    disabled_hash = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(
            text(
                """
                SELECT * FROM perchpoint.activate_invitation(
                  :token, :email, :subject, :disabled_hash
                )
                """
            ),
            {
                "token": _hash(token),
                "email": email,
                "subject": provider_subject,
                "disabled_hash": disabled_hash,
            },
        ).mappings().first()
    return None if row is None else dict(row)


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


def list_factors(settings: Settings, account: UUID, organization: UUID) -> list[dict]:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT provider_factor_id, kind, confirmed_at
                FROM identity_factors
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                )
                  AND removed_at IS NULL
                ORDER BY created_at
                """
            ),
            {"account": account},
        ).mappings().all()
    return [dict(row) for row in rows]


def mark_factor_removed(
    settings: Settings,
    account: UUID,
    organization: UUID,
    provider_factor_id: str,
) -> bool:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE identity_factors
                SET removed_at = now()
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                )
                  AND provider_factor_id = :factor
                  AND removed_at IS NULL
                """
            ),
            {"account": account, "factor": provider_factor_id},
        ).rowcount
        if updated:
            connection.execute(
                text("SELECT perchpoint.revoke_account_sessions(:account, 'mfa_factor_removed')"),
                {"account": account},
            )
    return bool(updated)


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


def matching_recovery_code(settings: Settings, account: UUID, code: str) -> UUID | None:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        rows = connection.execute(
            text("SELECT * FROM perchpoint.recovery_code_material(:account)"),
            {"account": account},
        ).mappings().all()
    matched = next(
        (
            row
            for row in rows
            if bcrypt.checkpw(code.encode(), str(row["code_hash"]).encode())
        ),
        None,
    )
    return None if matched is None else matched["code_id"]


def consume_recovery_code_id(settings: Settings, account: UUID, code_id: UUID) -> bool:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        consumed = connection.execute(
            text("SELECT perchpoint.consume_recovery_code(:account, :code_id)"),
            {"account": account, "code_id": code_id},
        ).scalar()
        if consumed:
            connection.execute(
                text("SELECT perchpoint.revoke_account_sessions(:account, 'mfa_recovery')"),
                {"account": account},
            )
    return bool(consumed)


def consume_recovery_code(settings: Settings, account: UUID, code: str) -> bool:
    code_id = matching_recovery_code(settings, account, code)
    return False if code_id is None else consume_recovery_code_id(settings, account, code_id)


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
    resource_type: str = "organization",
    resource_id: UUID | None = None,
    decision_types: list[str] | None = None,
    approval_id: UUID | None = None,
) -> str:
    if grantor == grantee:
        raise ValueError("self_delegation")
    if days < 1 or days > 30:
        raise ValueError("delegation_window")
    if capability in OWNER_RESERVED:
        raise ValueError("owner_reserved")
    delegation_id = uuid4()
    with runtime_transaction(settings, grantor, organization, uuid4()) as connection:
        grantor_role = connection.execute(
            text("SELECT role_name FROM perchpoint.current_membership(:account)"),
            {"account": grantor},
        ).scalar()
        if capability not in BUNDLES.get(str(grantor_role), frozenset()):
            raise ValueError("capability_not_held")
        grantee_active = connection.execute(
            text("SELECT perchpoint.active_org_member(:grantee)"),
            {"grantee": grantee},
        ).scalar()
        if not grantee_active:
            raise ValueError("grantee_unavailable")
        if approval_id is None or approval_id in {grantor, grantee}:
            raise ValueError("delegation_independent_owner_approval_required")
        owner_approval = connection.execute(
            text(
                """
                SELECT 1 FROM memberships
                WHERE organization_id = :org
                  AND account_id = :approver
                  AND role_name = 'owner'
                  AND effective_at <= now()
                  AND (ended_at IS NULL OR ended_at > now())
                """
            ),
            {"org": organization, "approver": approval_id},
        ).scalar()
        if not owner_approval:
            raise ValueError("delegation_independent_owner_approval_required")
        decisions = decision_types or []
        if resource_id is None or not decisions:
            raise ValueError("delegation_bounds_required")
        if resource_type == "organization" and resource_id != organization:
            raise ValueError("delegation_bounds_required")
        if capability == "expense.approve":
            catalog_rows = connection.execute(
                text(
                    """
                    SELECT decision_type, financial, capital, owner_reserved
                    FROM business_action_catalog
                    WHERE decision_type = ANY(:decisions)
                    """
                ),
                {"decisions": decisions},
            ).mappings().all()
            if (
                resource_type != "property"
                or amount_ceiling_minor is None
                or amount_ceiling_minor > 120_000
                or len(catalog_rows) != len(set(decisions))
                or any(
                    not row["financial"] or row["capital"] or row["owner_reserved"]
                    for row in catalog_rows
                )
            ):
                raise ValueError("delegation_financial_bounds_invalid")
        connection.execute(
            text(
                """
                INSERT INTO delegations (
                  organization_id, id, grantor_id, grantee_id, capability,
                  amount_ceiling_minor, resource_type, resource_id, decision_types,
                  approved_by, ends_at, status, reason
                ) VALUES (
                  :org, :id, :grantor, :grantee, :capability,
                  :ceiling, :resource_type, :resource_id, :decision_types,
                  :approval_id, now() + make_interval(days => :days), 'active', :reason
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
                "resource_type": resource_type,
                "resource_id": resource_id,
                "decision_types": decision_types or [],
                "approval_id": approval_id,
                "days": days,
                "reason": reason,
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO delegation_events (
                  organization_id, id, delegation_id, actor_id, action, details
                ) VALUES (
                  :org, :event, :delegation, :actor, 'created',
                  jsonb_build_object('policy_version', 'phase6-1')
                )
                """
            ),
            {
                "org": organization,
                "event": uuid4(),
                "delegation": delegation_id,
                "actor": grantor,
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


def resend_invitation(settings: Settings, actor: UUID, organization: UUID, invitation_id: UUID) -> dict:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        row = connection.execute(
            text(
                """
                SELECT email, role_name, purpose,
                       expires_at - created_at <= interval '24 hours' AS staff
                FROM identity_invitations
                WHERE id = :id AND organization_id = :org AND inviter_id = :actor
                  AND accepted_at IS NULL AND revoked_at IS NULL AND expires_at > now()
                """
            ),
            {"id": invitation_id, "org": organization, "actor": actor},
        ).mappings().first()
    if row is None:
        raise ValueError("invitation_invalid")
    replacement = create_invitation(
        settings,
        actor,
        organization,
        row["email"],
        row["role_name"],
        row["purpose"],
        staff=bool(row["staff"]),
    )
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        connection.execute(
            text(
                """
                UPDATE identity_invitations
                SET revoked_at = now(), replaced_by = :replacement
                WHERE id = :id AND organization_id = :org AND accepted_at IS NULL AND revoked_at IS NULL
                """
            ),
            {
                "replacement": UUID(replacement["invitation_id"]),
                "id": invitation_id,
                "org": organization,
            },
        )
    return replacement


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
        if updated:
            connection.execute(
                text(
                    """
                    INSERT INTO delegation_events (
                      organization_id, id, delegation_id, actor_id, action
                    ) VALUES (:org, :event, :delegation, :actor, 'revoked')
                    """
                ),
                {
                    "org": organization,
                    "event": uuid4(),
                    "delegation": delegation_id,
                    "actor": actor,
                },
            )
    if not updated:
        raise ValueError("delegation_invalid")


def expire_delegation(settings: Settings, actor: UUID, organization: UUID, delegation_id: UUID) -> None:
    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE delegations
                SET status = 'expired', ends_at = now()
                WHERE id = :id AND organization_id = :org AND grantor_id = :actor AND status = 'active'
                """
            ),
            {"id": delegation_id, "org": organization, "actor": actor},
        ).rowcount
        if updated:
            connection.execute(
                text(
                    """
                    INSERT INTO delegation_events (
                      organization_id, id, delegation_id, actor_id, action
                    ) VALUES (:org, :event, :delegation, :actor, 'expired')
                    """
                ),
                {
                    "org": organization,
                    "event": uuid4(),
                    "delegation": delegation_id,
                    "actor": actor,
                },
            )
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


def revoke_session(settings: Settings, account: UUID, organization: UUID, session_id: UUID) -> bool:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE identity_sessions
                SET revoked_at = now(), revoke_reason = 'user_revoked'
                WHERE id = :id AND revoked_at IS NULL
                  AND identity_id IN (
                    SELECT id FROM identity_accounts WHERE account_id = :account
                  )
                """
            ),
            {"id": session_id, "account": account},
        ).rowcount
    return bool(updated)


def select_context(settings: Settings, account: UUID, organization: UUID, session_id: UUID, membership_id: UUID) -> dict:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        rows = connection.execute(text("SELECT * FROM perchpoint.list_memberships(:account)"), {"account": account}).mappings().all()
        match = next((row for row in rows if row["membership_id"] == membership_id), None)
        if match is None:
            raise ValueError("context_invalid")
        connection.execute(
            text(
                """
                UPDATE identity_sessions
                SET organization_id = :org,
                    context_membership = :membership,
                    token_hash = :token_hash,
                    csrf_hash = :csrf_hash,
                    last_seen_at = now()
                WHERE id = :id AND revoked_at IS NULL
                """
            ),
            {
                "org": match["organization_id"],
                "membership": membership_id,
                "token_hash": _hash(token),
                "csrf_hash": _hash(csrf),
                "id": session_id,
            },
        )
    return {
        "organization_id": str(match["organization_id"]),
        "membership_id": str(membership_id),
        "role_name": match["role_name"],
        "token": token,
        "csrf": csrf,
    }


def create_access_request(
    settings: Settings,
    requester: UUID,
    organization: UUID,
    capability: str,
    purpose: str,
    scope_type: str,
    scope_resource_id: UUID | None,
    duration_hours: int,
    justification: str,
) -> str:
    if duration_hours < 1 or duration_hours > 720:
        raise ValueError("access_duration_invalid")
    request_id = uuid4()
    with runtime_transaction(settings, requester, organization, uuid4()) as connection:
        if connection.execute(
            text("SELECT 1 FROM capabilities WHERE code = :capability"),
            {"capability": capability},
        ).scalar() is None:
            raise ValueError("capability_invalid")
        connection.execute(
            text(
                """
                INSERT INTO access_requests (
                  organization_id, id, requester_id, capability, purpose,
                  scope_type, scope_resource_id, requested_until, justification, status
                )
                VALUES (
                  :org, :id, :requester, :capability, :purpose,
                  :scope_type, :scope_resource, now() + make_interval(hours => :duration),
                  :justification, 'pending'
                )
                """
            ),
            {
                "org": organization,
                "id": request_id,
                "requester": requester,
                "capability": capability,
                "purpose": purpose,
                "scope_type": scope_type,
                "scope_resource": scope_resource_id,
                "duration": duration_hours,
                "justification": justification,
            },
        )
    return str(request_id)


def decide_access_request(settings: Settings, approver: UUID, organization: UUID, request_id: UUID, approve: bool) -> None:
    with runtime_transaction(settings, approver, organization, uuid4()) as connection:
        row = connection.execute(
            text(
                """
                SELECT requester_id, capability, purpose, scope_type,
                       scope_resource_id, requested_until, justification
                FROM access_requests
                WHERE id = :id AND organization_id = :org AND status = 'pending'
                FOR UPDATE
                """
            ),
            {"id": request_id, "org": organization},
        ).mappings().first()
        if row is None:
            raise ValueError("request_missing")
        if row["requester_id"] == approver:
            raise ValueError("self_approval")
        materially_privileged = row["capability"] in {
            "approval.owner",
            "role.manage",
            "scope.manage",
            "delegation.grant",
            "service.manage",
            "security.read",
            "export.create",
        }
        if materially_privileged and connection.execute(
            text("SELECT perchpoint.current_role() = 'owner'")
        ).scalar() is not True:
            raise ValueError("independent_owner_approval_required")
        connection.execute(
            text(
                """
                UPDATE access_requests
                SET status = :status, approver_id = :approver, decided_at = now()
                WHERE id = :id
                """
            ),
            {"status": "approved" if approve else "denied", "approver": approver, "id": request_id},
        )
        if approve:
            membership_id = connection.execute(
                text(
                    """
                    SELECT id FROM memberships
                    WHERE account_id = :requester AND organization_id = :org
                      AND effective_at <= now() AND (ended_at IS NULL OR ended_at > now())
                    ORDER BY effective_at DESC LIMIT 1
                    """
                ),
                {"requester": row["requester_id"], "org": organization},
            ).scalar()
            if membership_id is None:
                raise ValueError("requester_membership_inactive")
            connection.execute(
                text(
                    """
                    INSERT INTO access_grants (
                      organization_id, id, account_id, membership_id, capability,
                      scope_type, scope_resource_id, purpose, justification,
                      ends_at, approved_by, access_request_id
                    ) VALUES (
                      :org, :id, :account, :membership, :capability,
                      :scope_type, :scope_resource, :purpose, :justification,
                      :ends_at, :approver, :request
                    )
                    """
                ),
                {
                    "org": organization,
                    "id": uuid4(),
                    "account": row["requester_id"],
                    "membership": membership_id,
                    "capability": row["capability"],
                    "scope_type": row["scope_type"],
                    "scope_resource": row["scope_resource_id"],
                    "purpose": row["purpose"],
                    "justification": row["justification"],
                    "ends_at": row["requested_until"],
                    "approver": approver,
                    "request": request_id,
                },
            )


def issue_service_credential(settings: Settings, actor: UUID, organization: UUID, principal_id: UUID) -> dict:
    secret = secrets.token_urlsafe(32)
    credential_id = uuid4()
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
                UPDATE service_credentials
                SET revoked_at = now()
                WHERE organization_id = :org AND principal_id = :principal
                  AND revoked_at IS NULL
                """
            ),
            {"org": organization, "principal": principal_id},
        )
        connection.execute(
            text(
                """
                INSERT INTO service_credentials (
                  organization_id, id, principal_id, verifier_hash, expires_at, bound_worker_name
                )
                SELECT :org, :id, principal.id, :verifier, now() + interval '1 day', principal.name
                FROM service_principals principal
                WHERE principal.organization_id = :org AND principal.id = :principal
                """
            ),
            {"org": organization, "id": credential_id, "principal": principal_id, "verifier": _hash(secret)},
        )
    return {"credential_id": str(credential_id), "credential": secret}


def authenticate_service_credential(
    settings: Settings,
    secret: str,
    *,
    audience: str,
    worker_name: str,
) -> dict | None:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(
            text(
                """
                SELECT * FROM perchpoint.authenticate_service_credential(
                  :verifier, :audience, :worker
                )
                """
            ),
            {
                "verifier": _hash(secret),
                "audience": audience,
                "worker": worker_name,
            },
        ).mappings().first()
    if row is None:
        return None
    return {
        "id": row["principal_id"],
        "organization_id": row["organization_id"],
        "service_principal": True,
        "assurance": "aal2",
        "membership_id": None,
    }


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


def approve_privileged_recovery(
    settings: Settings,
    approver: UUID,
    organization: UUID,
    recovery_id: UUID,
) -> None:
    with runtime_transaction(settings, approver, organization, uuid4()) as connection:
        updated = connection.execute(
            text(
                """
                UPDATE privileged_recoveries
                SET status = 'ready'
                WHERE organization_id = :org
                  AND id = :id
                  AND approver_account = :approver
                  AND subject_account <> :approver
                  AND status = 'waiting'
                """
            ),
            {"org": organization, "id": recovery_id, "approver": approver},
        ).rowcount
    if not updated:
        raise ValueError("recovery_approval_invalid")


def complete_privileged_recovery(
    settings: Settings,
    initiator: UUID,
    organization: UUID,
    recovery_id: UUID,
) -> UUID:
    with runtime_transaction(settings, initiator, organization, uuid4()) as connection:
        row = connection.execute(
            text(
                """
                SELECT subject_account, approver_account, status, not_before
                FROM privileged_recoveries
                WHERE organization_id = :org
                  AND id = :id
                  AND initiator_account = :initiator
                FOR UPDATE
                """
            ),
            {"org": organization, "id": recovery_id, "initiator": initiator},
        ).mappings().first()
        if row is None:
            raise ValueError("recovery_missing")
        if row["not_before"] > datetime.now(timezone.utc):
            raise ValueError("recovery_cooling")
        if row["approver_account"] is not None and row["status"] != "ready":
            raise ValueError("recovery_approval_required")
        if row["status"] not in {"waiting", "ready"}:
            raise ValueError("recovery_invalid")
        connection.execute(
            text(
                """
                UPDATE identity_factors
                SET removed_at = COALESCE(removed_at, now())
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :subject
                )
                """
            ),
            {"subject": row["subject_account"]},
        )
        connection.execute(
            text("SELECT perchpoint.revoke_account_sessions(:account, 'privileged_recovery')"),
            {"account": row["subject_account"]},
        )
        connection.execute(
            text(
                """
                UPDATE privileged_recoveries
                SET status = 'completed'
                WHERE organization_id = :org AND id = :id
                """
            ),
            {"org": organization, "id": recovery_id},
        )
    return row["subject_account"]


def revoke(settings: Settings, account: UUID, organization: UUID, session_id: UUID, reason: str) -> None:
    with runtime_transaction(settings, account, organization, uuid4()) as connection:
        connection.execute(
            text("UPDATE identity_sessions SET revoked_at = now(), revoke_reason = :reason WHERE id = :id AND revoked_at IS NULL"),
            {"id": session_id, "reason": reason},
        )

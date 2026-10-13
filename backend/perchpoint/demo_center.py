"""Local-only synthetic persona entry.

A persona session is issued by the server. The browser cannot choose a role by
itself. This module refuses to run unless the process is an explicit local demo.
"""
from __future__ import annotations

import json
import os
import secrets
from pathlib import Path
from uuid import UUID, uuid4, uuid5

import bcrypt
from sqlalchemy import text

from .db import engine_for
from .demo_catalog import (
    FEATURES,
    HOUSEHOLDS,
    account_for_slug,
    document_html,
    account_statement,
    cohort_summary,
    household_for_email,
    staff_accounts,
    work_items,
)
from .phase6_identity import open_session, resolve, revoke
from .settings import Settings

DEMO_NAMESPACE = UUID("6d7c2a1e-4b0f-5d33-9a18-0c5e7b2d44a1")
ORG_NAME = "HawkVision Homes — synthetic organization"

PERSONAS = (
    {"id": "platform_admin", "email": "dossnathan1@gmail.com", "role": "platform_admin", "title": "Technical operator", "summary": "Configuration, access, and demo status. Not a business approver.", "workspace": "/access/onboarding"},
    {"id": "owner", "email": "dossnathan@gmail.com", "role": "owner", "title": "Owner", "summary": "Portfolio, approvals, and owner-only decisions for the synthetic organization.", "workspace": "/owner"},
    {"id": "operations", "email": "operations@demo.perchpoint.invalid", "role": "operations_manager", "title": "Operations manager", "summary": "Leasing, screening, activation, and resident-account operations.", "workspace": "/leasing-desk"},
    {"id": "leasing", "email": "leasing@demo.perchpoint.invalid", "role": "leasing", "title": "Leasing staff", "summary": "Inquiries, showings, and applications.", "workspace": "/applications"},
    {"id": "resident", "email": "dossnathan2@gmail.com", "role": "resident", "title": "Resident", "summary": "One household portal, documents, and the derived account.", "workspace": "/portal"},
    {"id": "maintenance", "email": "maintenance@demo.perchpoint.invalid", "role": "maintenance", "title": "Maintenance coordinator", "summary": "Synthetic maintenance queue. This is not live 24/7 coverage or production dispatch.", "workspace": "/maintenance"},
    {"id": "technician", "email": "technician@demo.perchpoint.invalid", "role": "technician", "title": "Technician", "summary": "Synthetic jobs, time, and evidence. This is not a native field app.", "workspace": "/maintenance/jobs"},
)


def demo_enabled() -> bool:
    environment = os.environ.get("PHASE3_ENVIRONMENT", "local")
    return (
        environment in {"local", "test"}
        and os.environ.get("PHASE2_LOCAL_AUTH") == "development"
        and os.environ.get("DEMO_MODE") == "1"
    )


def persona(persona_id: str) -> dict | None:
    for row in PERSONAS:
        if row["id"] == persona_id:
            return row
    return None


def accepts_local_demo_password(email: str, password: str) -> bool:
    """True only for a local demo identity using the ignored local password.

    This does not change the 15-character rule for any other account.
    """
    if not demo_enabled() or persona_by_email(email) is None:
        return False
    configured = os.environ.get("PERCHPOINT_LOCAL_DEMO_PASSWORD", "")
    if len(configured) < 12 or len(password) != len(configured):
        return False
    return secrets.compare_digest(password, configured)


def persona_by_email(email: str) -> dict | None:
    normalized = email.strip().lower()
    for row in PERSONAS:
        if row["email"].lower() == normalized:
            return row
    for household in HOUSEHOLDS:
        if household["email"].lower() == normalized:
            return {
                "id": f"resident-{household['number']:02d}",
                "email": household["email"],
                "role": "resident",
                "title": "Resident",
                "summary": household["home_label"],
                "workspace": "/portal",
            }
    return None


def feature_inventory() -> list[dict]:
    return [dict(row) for row in FEATURES]


def _admin(settings: Settings):
    return engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")


def _organization(settings: Settings) -> UUID:
    with _admin(settings).connect() as connection:
        found = connection.execute(
            text("SELECT id FROM organizations WHERE name LIKE 'HawkVision Homes%' ORDER BY name LIMIT 1")
        ).scalar()
    if found is None:
        raise LookupError("synthetic organization is not seeded")
    return found


def _ensure_principal(settings: Settings, row: dict, organization: UUID) -> tuple[UUID, UUID]:
    membership_id = uuid5(DEMO_NAMESPACE, f"membership:{row['email']}")
    password_hash = bcrypt.hashpw(secrets.token_bytes(32), bcrypt.gensalt()).decode()
    with _admin(settings).begin() as connection:
        account_id = connection.execute(
            text("SELECT id FROM accounts WHERE lower(email) = lower(:email)"),
            {"email": row["email"]},
        ).scalar()
        if account_id is None:
            account_id = uuid5(DEMO_NAMESPACE, row["email"])
            connection.execute(
                text("INSERT INTO accounts (id, email, password_hash) VALUES (:id, :email, :password)"),
                {"id": account_id, "email": row["email"], "password": password_hash},
            )
        connection.execute(
            text(
                """
                UPDATE memberships
                SET ended_at = now()
                WHERE account_id = :account
                  AND organization_id = :org
                  AND role_name <> :role
                  AND ended_at IS NULL
                """
            ),
            {"account": account_id, "org": organization, "role": row["role"]},
        )
        connection.execute(
            text(
                """
                INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at, ended_at)
                VALUES (:id, :account, :org, :role, '1999-01-01T00:00:00Z', NULL)
                ON CONFLICT (id) DO UPDATE SET role_name = EXCLUDED.role_name, ended_at = NULL, account_id = EXCLUDED.account_id
                """
            ),
            {"id": membership_id, "account": account_id, "org": organization, "role": row["role"]},
        )
    return account_id, membership_id


HOUSEHOLD_ROLES = frozenset({"resident", "owner", "operations_manager", "leasing"})


def household_view(settings: Settings, token: str | None) -> dict:
    """One synthetic household for the signed-in demo persona.

    The staff portal API stays limited to inquiry.manage. This local read does
    not add that capability to a resident session.
    """
    if not demo_enabled():
        raise PermissionError("demo mode is closed")
    session = resolve(settings, token)
    if session is None or session.get("context_membership") is None:
        raise LookupError("signed out")
    with _admin(settings).connect() as connection:
        actor = connection.execute(
            text(
                """
                SELECT membership.role_name, account.email
                FROM memberships membership
                JOIN accounts account ON account.id = membership.account_id
                WHERE membership.id = :membership AND membership.account_id = :account
                """
            ),
            {"membership": session["context_membership"], "account": session["id"]},
        ).mappings().first()
        if actor is None or actor["role_name"] not in HOUSEHOLD_ROLES:
            raise PermissionError("household")
    if actor is None or actor["role_name"] != "resident":
        raise PermissionError("household")
    row = household_for_email(actor["email"])
    if row is None:
        raise LookupError("household")
    return {
        "person_label": row["person_label"],
        "home_label": row["home_label"],
        "state": "active",
        "sample_marker": row["sample_marker"],
        "organization": ORG_NAME,
        "rent_minor": row["rent_minor"],
        "due_minor": row["due_minor"],
        "past_due_minor": row["past_due_minor"],
        "credit_minor": row["credit_minor"],
        "disputed_minor": row["disputed_minor"],
        "account_status": row["status"],
        "currency": "USD",
        "synthetic": True,
        "payments_open": False,
        "maintenance_open": False,
        "messages_open": False,
        "guidance": "This is your household. Amounts are synthetic demonstration figures derived from the posted scenario. No money has moved.",
        "statement": account_statement(row),
        "requests": [item for item in _read_requests() if item["slug"] == row["slug"]],
    }


def _actor(settings: Settings, token: str | None) -> dict:
    if not demo_enabled():
        raise PermissionError("demo mode is closed")
    session = resolve(settings, token)
    if session is None or session.get("context_membership") is None:
        raise LookupError("signed out")
    with _admin(settings).connect() as connection:
        actor = connection.execute(
            text(
                """
                SELECT membership.role_name, account.email
                FROM memberships membership
                JOIN accounts account ON account.id = membership.account_id
                WHERE membership.id = :membership AND membership.account_id = :account
                """
            ),
            {"membership": session["context_membership"], "account": session["id"]},
        ).mappings().first()
    if actor is None:
        raise LookupError("signed out")
    return actor


def accounts_view(settings: Settings, token: str | None) -> dict:
    actor = _actor(settings, token)
    if actor["role_name"] not in {"owner", "operations_manager"}:
        raise PermissionError("accounts")
    summary = cohort_summary()
    return {
        "as_of": summary["as_of"],
        "currency": "USD",
        "money_moved": False,
        "past_due_minor": summary["past_due_minor"],
        "accounts": staff_accounts(),
    }


def account_detail(settings: Settings, token: str | None, slug: str) -> dict:
    actor = _actor(settings, token)
    if actor["role_name"] == "resident":
        own = household_for_email(actor["email"])
        if own is None or own["slug"] != slug:
            raise PermissionError("accounts")
        return account_statement(own)
    if actor["role_name"] not in {"owner", "operations_manager"}:
        raise PermissionError("accounts")
    row = account_for_slug(slug)
    if row is None:
        raise LookupError("account")
    return row


def document_view(settings: Settings, token: str | None, slug: str, kind: str) -> str:
    account = account_detail(settings, token, slug)
    try:
        return document_html(account, kind)
    except ValueError as exc:
        raise LookupError("document") from exc


def work_view(settings: Settings, token: str | None) -> dict:
    actor = _actor(settings, token)
    if actor["role_name"] not in {"owner", "operations_manager", "leasing"}:
        raise PermissionError("work")
    items = work_items()
    if actor["role_name"] == "leasing":
        items = [
            {key: value for key, value in item.items() if key != "amount_minor"}
            for item in items
            if item["workflow"] != "Dispute"
        ]
    for request in _read_requests():
        if request["state"] == "submitted":
            items.append({
                "id": request["id"],
                "workflow": "Request",
                "subject": f"{request['person_label']} asked to update {request['kind']}",
                "home_label": request["home_label"],
                "status": "Submitted",
                "assignee": "Operations manager",
                "age_days": 0,
                "next_action": "Review the household request. It does not change the lease.",
                "amount_minor": None,
            })
    return {"items": items, "synthetic": True, "money_moved": False, "can_review": actor["role_name"] in {"owner", "operations_manager"}}


REQUEST_FILE = Path(__file__).resolve().parents[1] / ".demo-requests.json"
REQUEST_KINDS = frozenset({"contact", "accessibility", "profile"})


def _read_requests() -> list[dict]:
    if not REQUEST_FILE.exists():
        return []
    payload = json.loads(REQUEST_FILE.read_text(encoding="utf-8"))
    return payload if isinstance(payload, list) else []


def _write_requests(rows: list[dict]) -> None:
    REQUEST_FILE.write_text(json.dumps(rows, indent=2), encoding="utf-8")


def submit_resident_request(settings: Settings, token: str | None, kind: str, note: str, idempotency_key: str) -> dict:
    actor = _actor(settings, token)
    if actor["role_name"] != "resident":
        raise PermissionError("request")
    household = household_for_email(actor["email"])
    if household is None or kind not in REQUEST_KINDS:
        raise ValueError("request")
    text_note = " ".join(note.split())
    if len(text_note) < 8 or len(text_note) > 500 or len(idempotency_key) < 8:
        raise ValueError("request")
    rows = _read_requests()
    for existing in rows:
        if existing["idempotency_key"] == idempotency_key and existing["slug"] == household["slug"]:
            return existing
    item = {
        "id": str(uuid4()),
        "idempotency_key": idempotency_key,
        "slug": household["slug"],
        "person_label": household["person_label"],
        "home_label": household["home_label"],
        "kind": kind,
        "note": text_note,
        "state": "submitted",
        "submitted_on": "2026-10-11",
    }
    rows.append(item)
    _write_requests(rows)
    return item


def review_resident_request(settings: Settings, token: str | None, request_id: str) -> dict:
    actor = _actor(settings, token)
    if actor["role_name"] not in {"owner", "operations_manager"}:
        raise PermissionError("request")
    rows = _read_requests()
    for item in rows:
        if item["id"] == request_id and item["state"] == "submitted":
            item["state"] = "reviewed"
            item["reviewed_by"] = actor["role_name"]
            _write_requests(rows)
            return item
    raise LookupError("request")


def owner_view(settings: Settings, token: str | None) -> dict:
    if not demo_enabled():
        raise PermissionError("demo mode is closed")
    session = resolve(settings, token)
    if session is None or session.get("context_membership") is None:
        raise LookupError("signed out")
    with _admin(settings).connect() as connection:
        actor = connection.execute(
            text(
                """
                SELECT membership.role_name, account.email
                FROM memberships membership
                JOIN accounts account ON account.id = membership.account_id
                WHERE membership.id = :membership AND membership.account_id = :account
                """
            ),
            {"membership": session["context_membership"], "account": session["id"]},
        ).mappings().first()
    owner = persona("owner")
    if actor is None or actor["role_name"] != "owner" or owner is None or actor["email"] != owner["email"]:
        raise PermissionError("owner")
    summary = cohort_summary()
    past_due = f"${summary['past_due_minor'] / 100:,.2f}"
    partial = f"${summary['partial_due_minor'] / 100:,.2f}"
    return {
        "organization": ORG_NAME,
        "role": "Owner",
        "email": actor["email"],
        "synthetic": True,
        "as_of": summary["as_of"],
        "briefing": f"As of {summary['as_of']}: {summary['homes']} leased homes and {summary['households']} households. {summary['past_due_accounts']} accounts are past due. {summary['open_disputes']} dispute needs a decision. These figures are synthetic and no money has moved.",
        "cards": [
            {"label": "Portfolio", "value": f"{summary['homes']} homes", "detail": f"{summary['occupied']} leased. {summary['future_availability']} have a future availability date and are not vacant today.", "href": "/rentals", "action": "Review the 20-home portfolio"},
            {"label": "Households", "value": str(summary["households"]), "detail": "One current household for each home in the demonstration cohort.", "href": "/portal", "action": "Open the resident household example"},
            {"label": "Past due", "value": f"{summary['past_due_accounts']} accounts", "detail": f"{past_due} past due as of {summary['as_of']}. This is not cash collected.", "href": "/owner/accounts/demo-17", "action": "View the past-due accounts"},
            {"label": "Partial settlements", "value": f"{summary['partial_accounts']} accounts", "detail": f"{partial} still open on partial settlements.", "href": "/owner/accounts/demo-13", "action": "View partial settlements"},
            {"label": "Decisions", "value": f"{summary['open_disputes']} open dispute", "detail": "Oakridge House has an open dispute on October rent. Capital work and spend above $1,200 still require the owner.", "href": "/owner/accounts/demo-20", "action": "Review the open dispute"},
            {"label": "Upcoming availability", "value": f"{summary['future_availability']} homes", "detail": "Available 2027-06-01, after the current lease. Not vacant today.", "href": "/rentals?availability=upcoming", "action": "See homes with a future date"},
        ],
        "attention": [
            account for account in staff_accounts()
            if account["past_due_minor"] or account["disputed_minor"] or account["scenario"] == "partial"
        ],
    }


def provision_local_demo_logins(settings: Settings) -> None:
    """Create separate local auth users for demo personas.

    The password comes from PERCHPOINT_LOCAL_DEMO_PASSWORD and is never logged.
    Outbound mail is not called.
    """
    if not demo_enabled():
        return
    password = os.environ.get("PERCHPOINT_LOCAL_DEMO_PASSWORD", "").strip()
    if not password:
        return
    from .phase6_provider import ProviderError, create_user, find_user_by_email, update_user_password

    organization = _organization(settings)
    known = {row["email"] for row in PERSONAS}
    extra: list[dict] = []
    for household in HOUSEHOLDS:
        persona = persona_by_email(household["email"])
        if persona is not None and persona["email"] not in known:
            extra.append(persona)
    for row in (*PERSONAS, *extra):
        _ensure_principal(settings, row, organization)
        try:
            create_user(row["email"], password)
        except ProviderError:
            found = find_user_by_email(row["email"])
            if found:
                try:
                    update_user_password(found, password)
                except ProviderError:
                    continue


def enter(settings: Settings, persona_id: str, previous_token: str | None) -> dict:
    if not demo_enabled():
        raise PermissionError("demo mode is closed")
    row = persona(persona_id)
    if row is None:
        raise KeyError(persona_id)
    organization = _organization(settings)
    previous = resolve(settings, previous_token)
    if previous is not None:
        revoke(settings, previous["id"], previous["organization_id"], previous["session_id"], "persona_switch")
    account_id, membership_id = _ensure_principal(settings, row, organization)
    subject = f"local:{row['email']}"
    with _admin(settings).connect() as connection:
        existing_subject = connection.execute(
            text("SELECT provider_subject FROM identity_accounts WHERE account_id = :account"),
            {"account": account_id},
        ).scalar()
    if existing_subject:
        subject = str(existing_subject)
    opened = open_session(
        settings,
        account_id,
        organization,
        row["role"],
        subject,
        "aal2",
        membership_id=membership_id,
        provider_session_id=f"demo:{row['id']}",
    )
    with _admin(settings).begin() as connection:
        connection.execute(
            text("UPDATE identity_sessions SET reauthenticated_at = now() WHERE id = :id"),
            {"id": opened["session_id"]},
        )
    return {
        "persona": row["id"],
        "email": row["email"],
        "role": row["role"],
        "title": row["title"],
        "workspace": row["workspace"],
        "organization": ORG_NAME,
        "organization_id": str(organization),
        "assurance": "aal2",
        "synthetic": True,
        "token": opened["token"],
        "csrf": opened["csrf"],
    }

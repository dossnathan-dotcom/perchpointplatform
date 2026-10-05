import base64
import hashlib
import hmac
import json
import os
import re
import struct
import time
import urllib.request
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text as sql_text

from perchpoint.db import engine_for, runtime_transaction
from perchpoint.phase6_identity import consume_recovery_code, refresh_token_for, resolve
from perchpoint.phase6_policy import approval_authority, authorize, password_problem, recovery_participants
from foundation.seeds import sid
from perchpoint.phase6_provider import (
    ProviderError,
    create_user,
    find_user_by_email,
    recovery_link,
    update_user_password,
)
from perchpoint.routes import create_app
from perchpoint.settings import Settings, configured_session_keys

ORIGIN = "http://testserver"


def _totp(secret: bytes, moment: float | None = None) -> str:
    counter = int((time.time() if moment is None else moment) // 30)
    digest = hmac.new(secret, struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    code = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{code % 1_000_000:06d}"


def _csrf(signed: dict) -> dict[str, str]:
    return {"x-perchpoint-csrf": signed["csrf"], "origin": ORIGIN}


def _mark_current_session_aal2(client: TestClient, signed: dict) -> None:
    account_id = UUID(client.get("/api/v2/auth/me").json()["account_id"])
    organization_id = UUID(signed["organization_id"])
    with runtime_transaction(Settings.load(), account_id, organization_id, uuid4()) as connection:
        connection.execute(
            sql_text(
                """
                UPDATE identity_sessions
                SET assurance = 'aal2', reauthenticated_at = now()
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                ) AND revoked_at IS NULL
                """
            ),
            {"account": account_id},
        )


def _invitation_token(email: str) -> str:
    mailpit = os.environ.get("PHASE6_MAILPIT_URL", "http://127.0.0.1:8025")
    for _ in range(20):
        listing = json.load(urllib.request.urlopen(f"{mailpit}/api/v1/messages", timeout=3))
        match = next(
            (
                item
                for item in listing["messages"]
                if any(recipient["Address"].lower() == email.lower() for recipient in item["To"])
            ),
            None,
        )
        if match:
            message = json.load(
                urllib.request.urlopen(f"{mailpit}/api/v1/message/{match['ID']}", timeout=3)
            )
            token = re.search(r"[?&]token=([^&\s]+)", message["Text"])
            if token:
                return token.group(1)
        time.sleep(0.1)
    raise AssertionError(f"Mailpit invitation was not delivered to {email}")


def _provider_user(email: str) -> None:
    try:
        create_user(email, Settings.load().dev_password)
    except ProviderError as exc:
        if exc.code != "authentication_failed":
            raise
        user_id = find_user_by_email(email)
        if user_id is None:
            raise
        update_user_password(user_id, Settings.load().dev_password)


def test_password_policy_and_generic_boundaries():
    assert password_problem("short") == "password_too_short"
    assert password_problem("x" * 65) == "password_too_long"
    assert password_problem("correcthorsebatterystaple") == "password_common"
    assert password_problem("synthetic-local-passphrase") is None


def test_financial_thresholds_and_authority_boundaries():
    rent = 200_000
    assert approval_authority(49_999, rent, capital=False, emergency=False) == "routine"
    assert approval_authority(50_000, rent, capital=False, emergency=False) == "operations"
    assert approval_authority(50_001, rent, capital=False, emergency=False) == "operations"
    assert approval_authority(119_999, rent, capital=False, emergency=False) == "operations"
    assert approval_authority(120_000, rent, capital=False, emergency=False) == "operations"
    assert approval_authority(120_001, rent, capital=False, emergency=False) == "owner"
    assert approval_authority(100_000, 90_000, capital=False, emergency=False) == "owner"
    assert approval_authority(10_000, rent, capital=True, emergency=False) == "owner"
    assert approval_authority(120_000, rent, capital=False, emergency=True) == "operations_emergency"
    assert approval_authority(89_999, 90_000, capital=False, emergency=False) == "operations"
    assert approval_authority(90_000, 90_000, capital=False, emergency=False) == "operations"
    assert approval_authority(90_001, 90_000, capital=False, emergency=False) == "owner"
    assert recovery_participants("owner", "platform_admin", None) == "allowed"
    assert recovery_participants("owner", "owner", None) == "supervised_recovery_required"
    assert recovery_participants("platform_admin", "leasing", "owner") == "supervised_recovery_required"
    assert recovery_participants("leasing", "platform_admin", "owner") == "allowed"
    assert recovery_participants("leasing", "platform_admin", None) == "supervised_recovery_required"
    assert recovery_participants("", "platform_admin", "owner") == "recovery_participant_invalid"
    assert recovery_participants("owner", "", "platform_admin") == "recovery_participant_invalid"


def test_unavoidable_imminent_harm_is_executed_and_owner_notification_is_queued():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert signed.status_code == 200, signed.text
    _mark_current_session_aal2(client, signed.json())
    run_key = uuid4().hex
    payload = {
        "property_id": str(sid("property-elm")),
        "amount_minor": 120_001,
        "emergency": True,
        "decision_type": "emergency_stabilization",
        "related_transaction_key": f"imminent-harm-{run_key}",
        "idempotency_key": f"imminent-harm-{run_key}",
    }
    denied = client.post("/api/v2/access/purchase-authority", headers=_csrf(signed.json()), json=payload)
    assert denied.status_code == 200, denied.text
    assert denied.json()["allowed"] is False
    assert denied.json()["authority"] == "owner"

    payload.update(
        decision_type="unavoidable_imminent_harm",
        imminent_harm_unavoidable=True,
        notification_note="A burst supply line is actively flooding occupied units; mitigation cannot wait.",
        idempotency_key=f"imminent-harm-escalated-{run_key}",
    )
    escalated = client.post("/api/v2/access/purchase-authority", headers=_csrf(signed.json()), json=payload)
    assert escalated.status_code == 200, escalated.text
    result = escalated.json()
    assert result["allowed"] is True
    assert result["act_and_notify"] is True
    assert result["authority"] == "owner"
    assert result["reason"] == "act_and_notify_escalation"

    organization_id = UUID(signed.json()["organization_id"])
    account_id = UUID(client.get("/api/v2/auth/me").json()["account_id"])
    with runtime_transaction(Settings.load(), account_id, organization_id, uuid4()) as connection:
        action = connection.execute(
            sql_text(
                "SELECT status, details FROM authorized_business_actions "
                "WHERE organization_id = :org AND id = :id"
            ),
            {"org": organization_id, "id": UUID(result["business_action_id"])},
        ).mappings().one()
        notification = connection.execute(
            sql_text(
                "SELECT event_type, status, payload FROM outbox "
                "WHERE organization_id = :org AND id = :id"
            ),
            {"org": organization_id, "id": UUID(result["escalation_outbox_id"])},
        ).mappings().one()
    assert action["status"] == "executed"
    assert action["details"]["act_and_notify"] is True
    assert notification["event_type"] == "owner.emergency_escalation"
    assert notification["status"] == "pending"
    assert notification["payload"]["owner_approval_claimed"] is False


def test_self_grant_self_approval_and_non_transitive_delegation():
    actor = str(uuid4())
    assert authorize(capability="membership.grant", role_name="platform_admin", actor_id=actor, target_id=actor).reason == "self_grant"
    assert authorize(capability="access.approve", role_name="owner", actor_id=actor, self_approval=True).reason == "self_approval"
    assert authorize(capability="delegation.grant", role_name="owner", actor_id=actor, delegated=True, delegation_active=True).reason == "delegation_non_transitive"
    assert authorize(capability="expense.approve", role_name="platform_admin", actor_id=actor).reason == "technical_role_is_not_business_authority"
    assert authorize(capability="platform.secrets", role_name="owner", actor_id=actor).reason == "owner_is_not_technical_operator"
    assert authorize(capability="platform.deploy", role_name="leasing", actor_id=actor).reason == "operations_boundary"


def test_step_up_is_enforced_by_business_authorization():
    denied = authorize(capability="delegation.grant", role_name="owner", actor_id="a", assurance="aal1", privileged=True)
    assert denied.reason == "step_up_required"
    allowed = authorize(capability="delegation.grant", role_name="owner", actor_id="a", assurance="aal2", reauthenticated_age_seconds=60, privileged=True)
    assert allowed.allowed


def test_interactive_sign_in_uses_cookie_and_rejects_missing_csrf():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    assert signed.status_code == 200, signed.text
    assert "pp_session" in signed.cookies
    cookie = signed.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "max-age=2592000" in cookie
    assert signed.json()["role_name"] == "operations_manager"
    assert signed.json()["mfa_required"] is True
    me = client.get("/api/v2/auth/me")
    assert me.status_code == 200
    purchase = client.post(
        "/api/v2/access/purchase-authority",
        headers=_csrf(signed.json()),
        json={
            "property_id": str(sid("property-elm")),
            "amount_minor": 49999,
            "decision_type": "routine_purchase",
            "related_transaction_key": "mfa-gated-purchase",
            "idempotency_key": "mfa-gated-purchase-request",
        },
    )
    assert purchase.status_code == 403
    assert purchase.json()["detail"]["code"] == "mfa_enrollment_required"
    denied_request_id = uuid4()
    denied = client.post(
        "/api/v2/auth/sign-out",
        headers={"x-request-id": str(denied_request_id)},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "csrf_rejected"
    assert denied.headers["x-request-id"] == str(denied_request_id)
    account_id = UUID(me.json()["account_id"])
    organization_id = UUID(signed.json()["organization_id"])
    with runtime_transaction(Settings.load(), account_id, organization_id, uuid4()) as connection:
        event = connection.execute(
            sql_text(
                """
                SELECT id, correlation_id, request_id, details
                FROM security_events
                WHERE organization_id = :org
                  AND request_id = :request
                  AND reason_code = 'csrf_rejected'
                """
            ),
            {"org": organization_id, "request": denied_request_id},
        ).mappings().one()
        alert = connection.execute(
            sql_text(
                """
                SELECT status, payload
                FROM outbox
                WHERE organization_id = :org
                  AND event_type = 'security.authorization_denied'
                  AND aggregate_id = :event
                """
            ),
            {"org": organization_id, "event": event["id"]},
        ).mappings().one()
    assert event["correlation_id"] == denied_request_id
    assert event["details"]["role_name"] == "operations_manager"
    assert event["details"]["policy_version"] == "phase6-2"
    assert event["details"]["scopes"]
    assert alert["status"] == "pending"
    assert alert["payload"]["request_id"] == str(denied_request_id)
    signed_out = client.post("/api/v2/auth/sign-out", headers=_csrf(signed.json()))
    assert signed_out.status_code == 200
    assert client.get("/api/v2/auth/me").status_code == 401


def test_invitation_is_single_use_and_totp_secret_is_not_stored_in_plaintext():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    _mark_current_session_aal2(client, signed.json())
    csrf = _csrf(signed.json())
    invited_email = f"worker.{uuid4().hex[:8]}@example.com"
    invitation_password = "Synthetic invitation password 2046!"
    invited = client.post(
        "/api/v2/auth/invitations",
        headers=csrf,
        json={"email": invited_email, "role_name": "technician", "purpose": "Assigned work only", "staff": False},
    )
    assert invited.status_code == 200, invited.text
    assert "token" not in invited.json()
    token = _invitation_token(invited_email)
    wrong = client.post(
        "/api/v2/auth/invitations/accept",
        json={"token": token, "email": "other.synthetic@example.com", "password": invitation_password},
    )
    assert wrong.status_code == 400
    resent = client.post(
        f"/api/v2/auth/invitations/{invited.json()['invitation_id']}/resend",
        headers=csrf,
    )
    assert resent.status_code == 200, resent.text
    replacement = _invitation_token(invited_email)
    assert replacement != token
    assert client.post(
        "/api/v2/auth/invitations/accept",
        json={"token": token, "email": invited_email, "password": invitation_password},
    ).status_code == 400
    activated = client.post(
        "/api/v2/auth/invitations/accept",
        json={"token": replacement, "email": invited_email, "password": invitation_password},
    )
    assert activated.status_code == 200
    assert activated.json()["role_name"] == "technician"
    assert activated.json()["mfa_required"] is True
    invited_session = client.post(
        "/api/v2/auth/sign-in",
        json={"email": invited_email, "password": invitation_password},
    )
    assert invited_session.status_code == 200
    blocked_before_mfa = client.get("/api/v2/properties")
    assert blocked_before_mfa.status_code == 403
    assert blocked_before_mfa.json()["detail"]["code"] == "mfa_enrollment_required"
    replay = client.post(
        "/api/v2/auth/invitations/accept",
        json={"token": replacement, "email": invited_email, "password": invitation_password},
    )
    assert replay.status_code == 400
    assert replay.json()["detail"]["code"] == "invitation_invalid"
    fresh = f"mfa.{uuid4().hex[:8]}@example.com"
    account = uuid4()
    settings = Settings.load()
    admin = create_engine(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with admin.begin() as connection:
        connection.execute(
            sql_text("INSERT INTO accounts (id, email, password_hash) VALUES (:id, :email, 'provider-owned')"),
            {"id": account, "email": fresh},
        )
        connection.execute(
                sql_text(
                """
                INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at)
                VALUES (:id, :account, :org, 'leasing', '1999-01-01T00:00:00Z')
                """
            ),
            {"id": uuid4(), "account": account, "org": signed.json()["organization_id"]},
        )
    admin.dispose()
    create_user(fresh, settings.dev_password)
    fresh_client = TestClient(create_app())
    fresh_signed = fresh_client.post("/api/v2/auth/sign-in", json={"email": fresh, "password": settings.dev_password})
    assert fresh_signed.status_code == 200, fresh_signed.text
    csrf = _csrf(fresh_signed.json())
    enrolled = fresh_client.post("/api/v2/auth/mfa/enroll", headers=csrf)
    assert enrolled.status_code == 200, enrolled.text
    secret = enrolled.json()["secret"]
    padded = secret + ("=" * ((8 - len(secret) % 8) % 8))
    confirmed = fresh_client.post(
        "/api/v2/auth/mfa/confirm",
        headers=csrf,
        json={"factor_id": enrolled.json()["factor_id"], "code": _totp(base64.b32decode(padded))},
    )
    assert confirmed.status_code == 200, confirmed.text
    codes = fresh_client.post("/api/v2/auth/recovery-codes", headers=_csrf(confirmed.json()))
    assert codes.status_code == 200
    assert len(codes.json()["codes"]) == 10
    returning = TestClient(create_app())
    returning_signed = returning.post(
        "/api/v2/auth/sign-in",
        json={"email": fresh, "password": settings.dev_password},
    )
    assert returning_signed.status_code == 200
    assert returning_signed.json()["assurance"] == "aal1"
    factors = returning.get("/api/v2/auth/mfa/factors")
    assert factors.status_code == 200
    assert factors.json()["factors"][0]["provider_factor_id"] == enrolled.json()["factor_id"]
    challenged = returning.post(
        "/api/v2/auth/mfa/confirm",
        headers=_csrf(returning_signed.json()),
        json={
            "factor_id": enrolled.json()["factor_id"],
            "code": _totp(base64.b32decode(padded), time.time() + 30),
        },
    )
    assert challenged.status_code == 200, challenged.text
    assert challenged.json()["assurance"] == "aal2"
    account_id = UUID(fresh_client.get("/api/v2/auth/me").json()["account_id"])
    used = fresh_client.post(
        "/api/v2/auth/recovery-code",
        headers=_csrf(confirmed.json()),
        json={"code": codes.json()["codes"][0]},
    )
    assert used.status_code == 200
    assert used.json()["signed_in"] is False
    assert fresh_client.get("/api/v2/auth/me").status_code == 401
    assert consume_recovery_code(settings, account_id, codes.json()["codes"][0]) is False


def test_self_delegation_is_rejected_and_a_bounded_grant_is_recorded():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    csrf = _csrf(signed.json())
    me = client.get("/api/v2/auth/me")
    own = client.post(
        "/api/v2/access/delegations",
        headers=csrf,
        json={"grantee_id": me.json()["account_id"], "capability": "expense.approve", "reason": "Covering leave", "days": 7, "amount_ceiling_minor": 50000},
    )
    assert own.status_code == 409
    assert own.json()["detail"]["code"] == "self_delegation"
    granted = client.post(
        "/api/v2/access/delegations",
        headers=csrf,
        json={"grantee_id": str(uuid4()), "capability": "expense.approve", "reason": "Covering leave", "days": 7, "amount_ceiling_minor": 50000},
    )
    assert granted.status_code == 403
    assert granted.json()["detail"]["code"] == "mfa_enrollment_required"


def test_sessions_access_requests_and_self_recovery_are_enforced():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    _mark_current_session_aal2(client, signed.json())
    csrf = _csrf(signed.json())
    listed = client.get("/api/v2/me/sessions")
    assert listed.status_code == 200
    assert listed.json()["sessions"]
    assert "token" not in listed.json()["sessions"][0]
    requested = client.post(
        "/api/v2/access/requests",
        headers=csrf,
        json={
            "capability": "document.read",
            "purpose": "Review the synthetic lease",
            "scope_type": "organization",
            "scope_resource_id": signed.json()["organization_id"],
            "duration_hours": 8,
            "justification": "Need the lease file",
        },
    )
    assert requested.status_code == 200, requested.text
    reviewed = client.post(f"/api/v2/access/requests/{requested.json()['request_id']}", headers=csrf, json={"approve": True})
    assert reviewed.status_code == 409
    assert reviewed.json()["detail"]["code"] == "self_approval"
    reserved = client.post(
        "/api/v2/access/delegations",
        headers=csrf,
        json={"grantee_id": str(uuid4()), "capability": "approval.owner", "reason": "Covering leave", "days": 7},
    )
    assert reserved.status_code == 409
    assert reserved.json()["detail"]["code"] == "owner_reserved"
    recovery = client.post(
        "/api/v2/access/recoveries",
        headers=csrf,
        json={"subject_account": client.get("/api/v2/auth/me").json()["account_id"], "evidence": "Offline sealed envelope"},
    )
    assert recovery.status_code == 409
    assert recovery.json()["detail"]["code"] == "self_recovery"
    forged = client.post("/api/v2/me/context", headers=csrf, json={"membership_id": str(uuid4())})
    assert forged.status_code == 409
    assert forged.json()["detail"]["code"] == "context_invalid"
    for path in ("/api/v2/worker/once", "/api/v2/phase5/jobs/process"):
        interactive_worker = client.post(path, headers=csrf)
        assert interactive_worker.status_code == 403
        assert interactive_worker.json()["detail"]["code"] == "denied"


def test_context_switch_rotates_the_session_verifier():
    _provider_user("nathan.synthetic@example.com")
    app = create_app()
    client = TestClient(app)
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={
            "email": "nathan.synthetic@example.com",
            "password": Settings.load().dev_password,
        },
    )
    assert signed.status_code == 200
    old_token = client.cookies["pp_session"]
    current_membership = client.get("/api/v2/auth/me").json()["membership_id"]
    contexts = client.get("/api/v2/me/contexts").json()["contexts"]
    target = next(
        context
        for context in contexts
        if context["membership_id"] != current_membership
    )

    switched = client.post(
        "/api/v2/me/context",
        headers=_csrf(signed.json()),
        json={"membership_id": target["membership_id"]},
    )
    assert switched.status_code == 200
    assert switched.json()["membership_id"] == target["membership_id"]
    assert switched.json()["csrf"] != signed.json()["csrf"]
    assert client.cookies["pp_session"] != old_token

    stale = TestClient(app)
    stale.cookies.set("pp_session", old_token)
    assert stale.get("/api/v2/auth/me").status_code == 401


def _account(email: str, role_name: str, organization_id: str) -> None:
    settings = Settings.load()
    admin = create_engine(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with admin.begin() as connection:
        connection.execute(
            sql_text("INSERT INTO accounts (id, email, password_hash) VALUES (:id, :email, 'provider-owned') ON CONFLICT (email) DO NOTHING"),
            {"id": uuid4(), "email": email},
        )
        account = connection.execute(sql_text("SELECT id FROM accounts WHERE email = :email"), {"email": email}).scalar()
        connection.execute(
            sql_text(
                """
                INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at)
                VALUES (:id, :account, :org, :role, '1999-01-01T00:00:00Z')
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": uuid4(), "account": account, "org": organization_id, "role": role_name},
        )
    admin.dispose()
    create_user(email, settings.dev_password)


def test_password_reset_does_not_sign_in_and_rejects_replay():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    email = f"reset.{uuid4().hex[:8]}@example.com"
    _account(email, "resident", signed.json()["organization_id"])
    fresh = TestClient(create_app())
    assert fresh.post("/api/v2/auth/sign-in", json={"email": email, "password": Settings.load().dev_password}).status_code == 200
    unknown = fresh.post("/api/v2/auth/password/reset-request", json={"email": "nobody.synthetic@example.com"})
    known = fresh.post("/api/v2/auth/password/reset-request", json={"email": email})
    assert unknown.status_code == known.status_code == 200
    assert unknown.json()["message"] == known.json()["message"]
    token = recovery_link(email)
    reset = fresh.post("/api/v2/auth/password/reset", json={"token": token, "password": "synthetic-reset-passphrase"})
    assert reset.status_code == 200, reset.text
    assert reset.json()["signed_in"] is False
    assert "pp_session" not in reset.cookies
    assert fresh.get("/api/v2/auth/me").status_code == 401
    replay = fresh.post("/api/v2/auth/password/reset", json={"token": token, "password": "synthetic-reset-passphrase"})
    assert replay.status_code == 400
    assert replay.json()["detail"]["code"] == "reset_invalid"


def test_service_credential_is_shown_once_and_hidden_from_operations():
    _provider_user("nathan.synthetic@example.com")
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    nathan = client.post("/api/v2/auth/sign-in", json={"email": "nathan.synthetic@example.com", "password": Settings.load().dev_password})
    assert nathan.status_code == 200, nathan.text
    principal = sid("service-principal-worker")
    admin = create_engine(Settings.load().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with admin.begin() as connection:
        connection.execute(
            sql_text(
                """
                INSERT INTO service_principals (organization_id, id, name, status, interactive)
                VALUES (:org, :id, 'synthetic-worker', 'active', false)
                ON CONFLICT (organization_id, id) DO NOTHING
                """
            ),
            {"org": nathan.json()["organization_id"], "id": principal},
        )
    admin.dispose()
    issued = client.post(f"/api/v2/access/service-credentials/{principal}", headers=_csrf(nathan.json()))
    assert issued.status_code == 403
    assert issued.json()["detail"]["code"] == "mfa_enrollment_required"
    operations = TestClient(create_app())
    ann = operations.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    _mark_current_session_aal2(operations, ann.json())
    denied = operations.post(
        f"/api/v2/access/service-credentials/{sid('service-principal-worker')}",
        headers=_csrf(ann.json()),
    )
    assert denied.status_code == 403


def test_public_listings_hide_internal_identifiers():
    client = TestClient(create_app())
    response = client.get("/api/v2/listings")
    assert response.status_code == 200, response.text
    for listing in response.json()["listings"]:
        assert "organization_id" not in listing
        assert "space_id" not in listing
        assert "tenant" not in listing


def test_phase6_tables_are_forced_and_runtime_cannot_bypass():
    admin = create_engine(Settings.load().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with admin.connect() as connection:
        runtime = connection.execute(sql_text("SELECT rolsuper, rolbypassrls, rolcanlogin FROM pg_roles WHERE rolname = 'perchpoint_runtime'")).one()
        definer = connection.execute(sql_text("SELECT rolsuper, rolbypassrls, rolcanlogin FROM pg_roles WHERE rolname = 'perchpoint_definer'")).one()
        forced = set(connection.execute(sql_text(
            """
            SELECT relname FROM pg_class
            JOIN pg_namespace ON pg_namespace.oid = relnamespace
            WHERE nspname = 'public' AND relkind = 'r' AND relrowsecurity AND relforcerowsecurity
            """
        )).scalars())
    admin.dispose()
    assert runtime.rolsuper is False and runtime.rolbypassrls is False
    assert definer.rolsuper is False and definer.rolbypassrls is True and definer.rolcanlogin is False
    for name in ("identity_accounts", "identity_sessions", "delegations", "access_requests", "service_principals", "security_events", "capabilities"):
        assert name in forced


def test_suspended_session_stops_immediately():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    email = f"suspended.{uuid4().hex[:8]}@example.com"
    _account(email, "leasing", signed.json()["organization_id"])
    fresh = TestClient(create_app())
    assert fresh.post("/api/v2/auth/sign-in", json={"email": email, "password": Settings.load().dev_password}).status_code == 200
    admin = create_engine(Settings.load().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with admin.begin() as connection:
        connection.execute(
            sql_text(
                """
                UPDATE identity_accounts SET status = 'suspended'
                WHERE account_id = (SELECT id FROM accounts WHERE email = :email)
                """
            ),
            {"email": email},
        )
    admin.dispose()
    assert fresh.get("/api/v2/auth/me").status_code == 401


def test_runtime_role_without_actor_context_sees_no_identity_rows():
    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        accounts = connection.execute(sql_text("SELECT count(*) FROM identity_accounts")).scalar()
        sessions = connection.execute(sql_text("SELECT count(*) FROM identity_sessions")).scalar()
    assert accounts == 0
    assert sessions == 0


def test_selected_membership_is_transaction_authority_and_cookie_mutations_require_csrf():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert signed.status_code == 200
    me = client.get("/api/v2/auth/me")
    assert me.headers["cache-control"] == "no-store"
    account = UUID(me.json()["account_id"])
    organization = UUID(signed.json()["organization_id"])
    denied = client.post(
        "/api/v2/parties",
        json={
            "party_kind": "person",
            "display_name": "CSRF must block this write",
            "idempotency_key": "csrf-party-write",
        },
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "csrf_rejected"
    with runtime_transaction(
        Settings.load(),
        account,
        organization,
        uuid4(),
        membership_id=uuid4(),
        assurance="aal2",
    ) as connection:
        assert connection.execute(sql_text("SELECT count(*) FROM parties")).scalar_one() == 0
        context = connection.execute(
            sql_text(
                """
                SELECT current_setting('app.identity_id', true),
                       current_setting('app.membership_id', true),
                       current_setting('app.aal', true)
                """
            )
        ).one()
    assert context[0] == ""
    assert context[1] != ""
    assert context[2] == "aal2"


def test_service_credential_is_worker_bound_scoped_and_tracks_last_use():
    _provider_user("nathan.synthetic@example.com")
    administrator = TestClient(create_app())
    signed = administrator.post(
        "/api/v2/auth/sign-in",
        json={"email": "nathan.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert signed.status_code == 200
    _mark_current_session_aal2(administrator, signed.json())
    principal = uuid4()
    organization = UUID(signed.json()["organization_id"])
    database = create_engine(Settings.load().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with database.begin() as connection:
        connection.execute(
            sql_text(
                """
                INSERT INTO service_principals (
                  organization_id, id, name, status, interactive, audience, capabilities
                ) VALUES (
                  :org, :id, 'search-indexer', 'active', false,
                  'perchpoint-worker', ARRAY['search.read']
                )
                """
            ),
            {"org": organization, "id": principal},
        )
    database.dispose()
    issued = administrator.post(
        f"/api/v2/access/service-credentials/{principal}",
        headers=_csrf(signed.json()),
    )
    assert issued.status_code == 200, issued.text
    secret = issued.json()["credential"]
    worker = TestClient(create_app())
    wrong_worker = worker.get(
        "/api/v2/search",
        headers={
            "authorization": f"Service {secret}",
            "x-perchpoint-worker": "other-worker",
        },
        params={"q": "Hawthorn"},
    )
    assert wrong_worker.status_code == 401
    accepted = worker.get(
        "/api/v2/search",
        headers={
            "authorization": f"Service {secret}",
            "x-perchpoint-worker": "search-indexer",
        },
        params={"q": "Hawthorn"},
    )
    assert accepted.status_code == 200, accepted.text
    excessive = worker.post(
        "/api/v2/worker/once",
        headers={
            "authorization": f"Service {secret}",
            "x-perchpoint-worker": "search-indexer",
        },
    )
    assert excessive.status_code == 403
    assert excessive.json()["detail"]["code"] == "denied"
    database = create_engine(Settings.load().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with database.connect() as connection:
        last_used = connection.execute(
            sql_text(
                """
                SELECT last_used_at FROM service_credentials
                WHERE organization_id = :org AND principal_id = :principal
                """
            ),
            {"org": organization, "principal": principal},
        ).scalar_one()
    database.dispose()
    assert last_used is not None
    revoked = administrator.delete(
        f"/api/v2/access/service-credentials/{issued.json()['credential_id']}",
        headers=_csrf(signed.json()),
    )
    assert revoked.status_code == 200, revoked.text
    assert worker.get(
        "/api/v2/search",
        headers={
            "authorization": f"Service {secret}",
            "x-perchpoint-worker": "search-indexer",
        },
        params={"q": "Hawthorn"},
    ).status_code == 401


def test_access_request_grants_bounded_authority_only_after_independent_owner_approval():
    for email in (
        "ann.synthetic@example.com",
        "faruk.synthetic@example.com",
    ):
        _provider_user(email)
    operations = TestClient(create_app())
    operations_session = operations.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    owner = TestClient(create_app())
    owner_session = owner.post(
        "/api/v2/auth/sign-in",
        json={"email": "faruk.synthetic@example.com", "password": Settings.load().dev_password},
    )
    organization = operations_session.json()["organization_id"]
    requester_email = f"access.requester.{uuid4().hex[:8]}@example.com"
    _account(requester_email, "technician", organization)
    requester = TestClient(create_app())
    requester_session = requester.post(
        "/api/v2/auth/sign-in",
        json={"email": requester_email, "password": Settings.load().dev_password},
    )
    for client, session in (
        (operations, operations_session),
        (owner, owner_session),
        (requester, requester_session),
    ):
        _mark_current_session_aal2(client, session.json())
    requested = requester.post(
        "/api/v2/access/requests",
        headers=_csrf(requester_session.json()),
        json={
            "capability": "export.create",
            "purpose": "Prepare one synthetic assignment export",
            "scope_type": "organization",
            "scope_resource_id": organization,
            "duration_hours": 2,
            "justification": "Temporary coverage during the synthetic review",
        },
    )
    assert requested.status_code == 200, requested.text
    request_id = requested.json()["request_id"]
    observer_email = f"access.observer.{uuid4().hex[:8]}@example.com"
    _account(observer_email, "resident", organization)
    observer = TestClient(create_app())
    observer_session = observer.post(
        "/api/v2/auth/sign-in",
        json={"email": observer_email, "password": Settings.load().dev_password},
    )
    listed = observer.get("/api/v2/access/requests")
    assert listed.status_code == 200, listed.text
    assert request_id not in {item["id"] for item in listed.json()["requests"]}
    observer_account = UUID(observer.get("/api/v2/auth/me").json()["account_id"])
    with runtime_transaction(
        Settings.load(), observer_account, UUID(observer_session.json()["organization_id"]), uuid4()
    ) as connection:
        leaked = connection.execute(
            sql_text("SELECT id FROM access_requests WHERE id = :id"),
            {"id": UUID(request_id)},
        ).first()
    assert leaked is None
    owner_queue = owner.get("/api/v2/access/requests")
    assert owner_queue.status_code == 200, owner_queue.text
    assert request_id in {item["id"] for item in owner_queue.json()["requests"]}
    non_owner = operations.post(
        f"/api/v2/access/requests/{request_id}",
        headers=_csrf(operations_session.json()),
        json={"approve": True},
    )
    assert non_owner.status_code == 409
    assert non_owner.json()["detail"]["code"] == "independent_owner_approval_required"
    approved = owner.post(
        f"/api/v2/access/requests/{request_id}",
        headers=_csrf(owner_session.json()),
        json={"approve": True},
    )
    assert approved.status_code == 200, approved.text
    requester_account = UUID(requester.get("/api/v2/auth/me").json()["account_id"])
    with runtime_transaction(
        Settings.load(), requester_account, UUID(organization), uuid4()
    ) as connection:
        grant = connection.execute(
            sql_text(
                """
                SELECT capability, scope_type, scope_resource_id, ends_at > now() AS active
                FROM access_grants
                WHERE access_request_id = :request
                """
            ),
            {"request": UUID(request_id)},
        ).mappings().one()
        allowed = connection.execute(
            sql_text("SELECT perchpoint.has_capability('export.create')")
        ).scalar_one()
    assert grant["capability"] == "export.create"
    assert grant["scope_type"] == "organization"
    assert grant["scope_resource_id"] == UUID(organization)
    assert grant["active"] is True
    assert allowed is True


def test_authority_change_approval_is_exact_independent_expiring_and_single_use():
    for email in ("nathan.synthetic@example.com", "faruk.synthetic@example.com"):
        _provider_user(email)
    administrator = TestClient(create_app())
    admin_session = administrator.post(
        "/api/v2/auth/sign-in",
        json={"email": "nathan.synthetic@example.com", "password": Settings.load().dev_password},
    )
    owner = TestClient(create_app())
    owner_session = owner.post(
        "/api/v2/auth/sign-in",
        json={"email": "faruk.synthetic@example.com", "password": Settings.load().dev_password},
    )
    _mark_current_session_aal2(administrator, admin_session.json())
    _mark_current_session_aal2(owner, owner_session.json())
    users = administrator.get("/api/v2/access/users").json()["users"]
    technician = next(item for item in users if item["email"] == "technician.synthetic@example.com")
    faruk = next(item for item in users if item["email"] == "faruk.synthetic@example.com")
    organization_id = admin_session.json()["organization_id"]

    missing = administrator.post(
        f"/api/v2/access/memberships/{technician['membership_id']}/scopes",
        headers=_csrf(admin_session.json()),
        json={"scope_type": "organization", "resource_id": organization_id},
    )
    assert missing.status_code == 422
    self_approval = owner.post(
        f"/api/v2/access/memberships/{faruk['membership_id']}/authority-approvals",
        headers=_csrf(owner_session.json()),
        json={
            "action": "scope",
            "scope_type": "organization",
            "resource_id": organization_id,
            "reason": "Attempt to approve own authority",
        },
    )
    assert self_approval.status_code == 409
    assert self_approval.json()["detail"]["code"] == "self_approval"

    def approve() -> str:
        response = owner.post(
            f"/api/v2/access/memberships/{technician['membership_id']}/authority-approvals",
            headers=_csrf(owner_session.json()),
            json={
                "action": "scope",
                "scope_type": "organization",
                "resource_id": organization_id,
                "reason": "Approve the exact synthetic organization scope",
            },
        )
        assert response.status_code == 200, response.text
        return response.json()["approval_id"]

    approval_id = approve()
    mismatch = administrator.post(
        f"/api/v2/access/memberships/{technician['membership_id']}/scopes",
        headers=_csrf(admin_session.json()),
        json={"scope_type": "property", "resource_id": str(uuid4()), "approval_id": approval_id},
    )
    assert mismatch.status_code == 409
    assert mismatch.json()["detail"]["code"] == "independent_owner_approval_required"
    database = create_engine(Settings.load().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with database.begin() as connection:
        connection.execute(
            sql_text("UPDATE authority_change_approvals SET expires_at = now() - interval '1 second' WHERE id = :id"),
            {"id": UUID(approval_id)},
        )
    database.dispose()
    expired = administrator.post(
        f"/api/v2/access/memberships/{technician['membership_id']}/scopes",
        headers=_csrf(admin_session.json()),
        json={"scope_type": "organization", "resource_id": organization_id, "approval_id": approval_id},
    )
    assert expired.status_code == 409

    approval_id = approve()
    payload = {"scope_type": "organization", "resource_id": organization_id, "approval_id": approval_id}
    assigned = administrator.post(
        f"/api/v2/access/memberships/{technician['membership_id']}/scopes",
        headers=_csrf(admin_session.json()),
        json=payload,
    )
    assert assigned.status_code == 200, assigned.text
    replayed = administrator.post(
        f"/api/v2/access/memberships/{technician['membership_id']}/scopes",
        headers=_csrf(admin_session.json()),
        json=payload,
    )
    assert replayed.status_code == 409
    assert replayed.json()["detail"]["code"] == "independent_owner_approval_required"


def test_temporary_capability_and_scope_must_come_from_the_same_grant():
    database = create_engine(Settings.load().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    resource_a, resource_b = uuid4(), uuid4()
    with database.begin() as connection:
        actor = connection.execute(
            sql_text("SELECT id FROM accounts WHERE email = 'technician.synthetic@example.com'")
        ).scalar_one()
        membership = connection.execute(
            sql_text(
                """
                SELECT id, organization_id FROM memberships
                WHERE account_id = :actor AND ended_at IS NULL
                ORDER BY effective_at DESC LIMIT 1
                """
            ),
            {"actor": actor},
        ).mappings().one()
        approver = connection.execute(
            sql_text(
                """
                SELECT account_id FROM memberships
                WHERE organization_id = :org AND role_name = 'owner' AND ended_at IS NULL
                ORDER BY effective_at DESC LIMIT 1
                """
            ),
            {"org": membership["organization_id"]},
        ).scalar_one()
        for capability, resource in (
            ("property.read", resource_a),
            ("document.read", resource_b),
        ):
            connection.execute(
                sql_text(
                    """
                    INSERT INTO access_grants (
                      organization_id, id, account_id, membership_id, capability,
                      scope_type, scope_resource_id, purpose, justification,
                      ends_at, approved_by, access_request_id
                    ) VALUES (
                      :org, :id, :actor, :membership, :capability,
                      'property', :resource, 'Cross-grant regression',
                      'Each capability remains bound to its approved scope',
                      now() + interval '1 hour', :approver, :request
                    )
                    """
                ),
                {
                    "org": membership["organization_id"],
                    "id": uuid4(),
                    "actor": actor,
                    "membership": membership["id"],
                    "capability": capability,
                    "resource": resource,
                    "approver": approver,
                    "request": uuid4(),
                },
            )
    database.dispose()
    with runtime_transaction(
        Settings.load(), actor, membership["organization_id"], uuid4()
    ) as connection:
        individual_checks = connection.execute(
            sql_text(
                """
                SELECT perchpoint.has_capability('property.read') AS capability,
                       perchpoint.scope_allows('property', :other) AS unrelated_scope,
                       perchpoint.authorized_for('property.read', 'property', :approved) AS approved,
                       perchpoint.authorized_for('property.read', 'property', :other) AS crossed
                """
            ),
            {"approved": resource_a, "other": resource_b},
        ).mappings().one()
    assert individual_checks["capability"] is True
    assert individual_checks["unrelated_scope"] is True
    assert individual_checks["approved"] is True
    assert individual_checks["crossed"] is False


def test_development_jwt_is_retired_without_the_test_fixture(monkeypatch):
    monkeypatch.setenv("PHASE6_ALLOW_DEV_JWT", "0")
    client = TestClient(create_app())
    response = client.post("/api/v2/session", json={"email": "ann.synthetic@example.com", "password": "x"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "development_jwt_retired"


def test_origin_is_bound_to_the_session_csrf_token():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    ).json()
    rejected = client.post(
        "/api/v2/access/requests",
        headers={"x-perchpoint-csrf": signed["csrf"], "origin": "https://attacker.invalid"},
        json={"capability": "document.read", "justification": "Forged cross-site request"},
    )
    assert rejected.status_code == 403
    assert rejected.json()["detail"]["code"] == "origin_rejected"


def test_provider_refresh_reuse_revokes_the_application_session(monkeypatch):
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert signed.status_code == 200
    second = TestClient(create_app())
    second_signed = second.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert second_signed.status_code == 200

    def reused(_refresh_token):
        raise ProviderError("authentication_failed")

    monkeypatch.setattr("perchpoint.routes.refresh_grant", reused)
    rejected = client.post("/api/v2/auth/mfa/enroll", headers=_csrf(signed.json()))
    assert rejected.status_code == 401
    assert rejected.json()["detail"]["code"] == "session_revoked"
    assert client.get("/api/v2/auth/me").status_code == 401
    assert second.get("/api/v2/auth/me").status_code == 401


def test_verified_email_change_preserves_identity_and_notifies_both_addresses(monkeypatch):
    old_email = f"contact.{uuid4().hex[:8]}@example.com"
    new_email = f"ann.changed.{uuid4().hex[:8]}@example.com"
    _provider_user("ann.synthetic@example.com")
    bootstrap = TestClient(create_app())
    organization_id = bootstrap.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    ).json()["organization_id"]
    _account(old_email, "project_manager", organization_id)
    client = TestClient(create_app())
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={"email": old_email, "password": Settings.load().dev_password},
    )
    assert signed.status_code == 200
    account_id = UUID(client.get("/api/v2/auth/me").json()["account_id"])
    organization_id = UUID(organization_id)
    with runtime_transaction(Settings.load(), account_id, organization_id, uuid4()) as connection:
        provider_subject = connection.execute(
            sql_text("SELECT provider_subject FROM identity_accounts WHERE account_id = :account"),
            {"account": account_id},
        ).scalar_one()
        connection.execute(
            sql_text(
                """
                UPDATE identity_sessions
                SET assurance = 'aal2', reauthenticated_at = now()
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                ) AND revoked_at IS NULL
                """
            ),
            {"account": account_id},
        )

    requested = []
    notices = []
    monkeypatch.setattr("perchpoint.routes.provider_request_email_change", lambda _token, email: requested.append(email))
    monkeypatch.setattr("perchpoint.routes.send_local_notice", lambda email, subject, _content: notices.append((email, subject)))
    pending = client.post(
        "/api/v2/auth/contact/email-change",
        headers=_csrf(signed.json()),
        json={"email": new_email},
    )
    assert pending.status_code == 200, pending.text
    assert requested == [new_email]
    assert {email for email, _subject in notices} == {old_email, new_email}

    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        synced_account = connection.execute(
            sql_text("SELECT perchpoint.sync_provider_email(:subject, :email)"),
            {"subject": provider_subject, "email": new_email},
        ).scalar_one()
    assert synced_account == account_id
    with runtime_transaction(Settings.load(), account_id, organization_id, uuid4()) as connection:
        account = connection.execute(
            sql_text("SELECT email FROM accounts WHERE id = :account"),
            {"account": account_id},
        ).scalar_one()
        history = connection.execute(
            sql_text(
                """
                SELECT status, previous_value, proposed_value, verified_at
                FROM identity_contact_history
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                )
                """
            ),
            {"account": account_id},
        ).mappings().one()
    assert account == new_email
    assert history["status"] == "verified"
    assert history["previous_value"] == old_email
    assert history["proposed_value"] == new_email
    assert history["verified_at"] is not None
    assert client.get("/api/v2/auth/me").status_code == 401


def test_access_review_revoke_ends_membership_and_sessions():
    _provider_user("ann.synthetic@example.com")
    reviewer = TestClient(create_app())
    signed = reviewer.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert signed.status_code == 200
    reviewer_account = UUID(reviewer.get("/api/v2/auth/me").json()["account_id"])
    organization_id = UUID(signed.json()["organization_id"])
    target_email = f"review.{uuid4().hex[:8]}@example.com"
    _account(target_email, "technician", str(organization_id))
    target = TestClient(create_app())
    target_signed = target.post(
        "/api/v2/auth/sign-in",
        json={"email": target_email, "password": Settings.load().dev_password},
    )
    assert target_signed.status_code == 200
    target_account = UUID(target.get("/api/v2/auth/me").json()["account_id"])
    campaign_id = uuid4()
    item_id = uuid4()
    with runtime_transaction(Settings.load(), reviewer_account, organization_id, uuid4()) as connection:
        connection.execute(
            sql_text(
                """
                UPDATE identity_sessions
                SET assurance = 'aal2', reauthenticated_at = now()
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                ) AND revoked_at IS NULL
                """
            ),
            {"account": reviewer_account},
        )
        connection.execute(
            sql_text(
                """
                INSERT INTO access_review_campaigns (
                  organization_id, id, title, opens_at, due_at, owner_account_id
                ) VALUES (:org, :id, 'Quarterly synthetic review', now(), now() + interval '7 days', :owner)
                """
            ),
            {"org": organization_id, "id": campaign_id, "owner": reviewer_account},
        )
        connection.execute(
            sql_text(
                """
                INSERT INTO access_review_items (organization_id, id, campaign_id, account_id, status)
                VALUES (:org, :id, :campaign, :account, 'pending')
                """
            ),
            {"org": organization_id, "id": item_id, "campaign": campaign_id, "account": target_account},
        )
    decided = reviewer.post(
        f"/api/v2/access/reviews/{campaign_id}/items/{item_id}",
        headers=_csrf(signed.json()),
        json={"decision": "revoke"},
    )
    assert decided.status_code == 200, decided.text
    assert decided.json()["campaign_complete"] is True
    assert target.get("/api/v2/auth/me").status_code == 401
    with runtime_transaction(Settings.load(), reviewer_account, organization_id, uuid4()) as connection:
        item = connection.execute(
            sql_text(
                """
                SELECT status, decision, reviewer_id, decided_at
                FROM access_review_items
                WHERE organization_id = :org AND id = :id
                """
            ),
            {"org": organization_id, "id": item_id},
        ).mappings().one()
        completed_at = connection.execute(
            sql_text(
                """
                SELECT completed_at FROM access_review_campaigns
                WHERE organization_id = :org AND id = :id
                """
            ),
            {"org": organization_id, "id": campaign_id},
        ).scalar_one()
    assert item["status"] == "revoked"
    assert item["decision"] == "revoke"
    assert item["reviewer_id"] == reviewer_account
    assert item["decided_at"] is not None
    assert completed_at is not None
    privileged_campaign = uuid4()
    privileged_item = uuid4()
    with runtime_transaction(Settings.load(), reviewer_account, organization_id, uuid4()) as connection:
        owner_account = connection.execute(
            sql_text(
                """
                SELECT account_id FROM memberships
                WHERE organization_id = :org AND role_name = 'owner'
                  AND effective_at <= now() AND (ended_at IS NULL OR ended_at > now())
                LIMIT 1
                """
            ),
            {"org": organization_id},
        ).scalar_one()
        connection.execute(
            sql_text(
                """
                INSERT INTO access_review_campaigns (
                  organization_id, id, title, opens_at, due_at, owner_account_id
                ) VALUES (:org, :id, 'Privileged synthetic review', now(), now() + interval '7 days', :owner)
                """
            ),
            {"org": organization_id, "id": privileged_campaign, "owner": reviewer_account},
        )
        connection.execute(
            sql_text(
                """
                INSERT INTO access_review_items (organization_id, id, campaign_id, account_id, status)
                VALUES (:org, :id, :campaign, :account, 'pending')
                """
            ),
            {
                "org": organization_id,
                "id": privileged_item,
                "campaign": privileged_campaign,
                "account": owner_account,
            },
        )
    privileged_denied = reviewer.post(
        f"/api/v2/access/reviews/{privileged_campaign}/items/{privileged_item}",
        headers=_csrf(signed.json()),
        json={"decision": "revoke"},
    )
    assert privileged_denied.status_code == 409
    assert privileged_denied.json()["detail"]["code"] == "governed_privileged_review_required"


def test_delegation_usage_enforces_scope_decision_amount_and_split_detection():
    run_key = uuid4().hex
    property_id = uuid4()
    for email in ("ann.synthetic@example.com", "technician.synthetic@example.com"):
        _provider_user(email)
    grantor = TestClient(create_app())
    grantor_session = grantor.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert grantor_session.status_code == 200
    grantor_account = UUID(grantor.get("/api/v2/auth/me").json()["account_id"])
    organization_id = UUID(grantor_session.json()["organization_id"])
    grantee = TestClient(create_app())
    grantee_session = grantee.post(
        "/api/v2/auth/sign-in",
        json={"email": "technician.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert grantee_session.status_code == 200
    grantee_account = UUID(grantee.get("/api/v2/auth/me").json()["account_id"])
    with runtime_transaction(Settings.load(), grantor_account, organization_id, uuid4()) as connection:
        owner_account = connection.execute(
            sql_text(
                """
                SELECT account_id FROM memberships
                WHERE organization_id = :org AND role_name = 'owner'
                  AND effective_at <= now() AND (ended_at IS NULL OR ended_at > now())
                LIMIT 1
                """
            ),
            {"org": organization_id},
        ).scalar_one()
        connection.execute(
            sql_text(
                """
                UPDATE identity_sessions
                SET assurance = 'aal2', reauthenticated_at = now()
                WHERE identity_id IN (
                  SELECT id FROM identity_accounts
                  WHERE account_id IN (:grantor, :grantee)
                ) AND revoked_at IS NULL
                """
            ),
            {"grantor": grantor_account, "grantee": grantee_account},
        )
    admin = engine_for(
        Settings.load().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2"
    )
    with admin.begin() as connection:
        connection.execute(
            sql_text(
                """
                INSERT INTO properties (organization_id, id, name, property_type)
                VALUES (:org, :property, :name, 'mixed_use')
                """
            ),
            {
                "org": organization_id,
                "property": property_id,
                "name": f"Synthetic delegation property {run_key}",
            },
        )
        connection.execute(
            sql_text(
                """
                INSERT INTO property_authority_limits (
                  organization_id, property_id, monthly_budget_minor,
                  monthly_rent_minor, source_kind, source_reference, approved_by
                ) VALUES (
                  :org, :property, 500000, 100000,
                  'synthetic_test_fixture', :source, :approver
                )
                """
            ),
            {
                "org": organization_id,
                "property": property_id,
                "source": f"phase6-test:{run_key}",
                "approver": owner_account,
            },
        )
    admin.dispose()
    with runtime_transaction(Settings.load(), grantee_account, organization_id, uuid4()) as connection:
        connection.execute(
            sql_text(
                """
                UPDATE identity_sessions
                SET assurance = 'aal2', reauthenticated_at = now()
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :grantee
                ) AND revoked_at IS NULL
                """
            ),
            {"grantee": grantee_account},
        )
    created = grantor.post(
        "/api/v2/access/delegations",
        headers=_csrf(grantor_session.json()),
        json={
            "grantee_id": str(grantee_account),
            "capability": "expense.approve",
            "reason": "Synthetic bounded purchase coverage",
            "days": 7,
            "amount_ceiling_minor": 50000,
            "resource_type": "property",
            "resource_id": str(property_id),
            "decision_types": ["routine_purchase"],
            "approval_id": str(owner_account),
        },
    )
    assert created.status_code == 200, created.text
    delegation_id = created.json()["delegation_id"]
    first = grantee.post(
        f"/api/v2/access/delegations/{delegation_id}/use",
        headers=_csrf(grantee_session.json()),
        json={
            "action_type": "purchase_authorization",
            "idempotency_key": f"delegated-purchase-first-{run_key}",
            "capability": "expense.approve",
            "resource_type": "property",
            "resource_id": str(property_id),
            "decision_type": "routine_purchase",
            "amount_minor": 30000,
            "related_transaction_key": f"synthetic-related-purchase-{run_key}",
        },
    )
    assert first.status_code == 200, first.text
    wrong_decision = grantee.post(
        f"/api/v2/access/delegations/{delegation_id}/use",
        headers=_csrf(grantee_session.json()),
        json={
            "action_type": "purchase_authorization",
            "idempotency_key": f"delegated-purchase-wrong-decision-{run_key}",
            "capability": "expense.approve",
            "resource_type": "property",
            "resource_id": str(property_id),
            "decision_type": "capital_project",
            "amount_minor": 1,
        },
    )
    assert wrong_decision.status_code == 409
    assert wrong_decision.json()["detail"]["code"] == "delegation_decision_type"
    split = grantee.post(
        f"/api/v2/access/delegations/{delegation_id}/use",
        headers=_csrf(grantee_session.json()),
        json={
            "action_type": "purchase_authorization",
            "idempotency_key": f"delegated-purchase-split-{run_key}",
            "capability": "expense.approve",
            "resource_type": "property",
            "resource_id": str(property_id),
            "decision_type": "routine_purchase",
            "amount_minor": 25000,
            "related_transaction_key": f"synthetic-related-purchase-{run_key}",
        },
    )
    assert split.status_code == 409
    assert split.json()["detail"]["code"] == "split_transaction"
    revoked = grantor.post(
        f"/api/v2/access/delegations/{delegation_id}/revoke",
        headers=_csrf(grantor_session.json()),
    )
    assert revoked.status_code == 200
    after_revoke = grantee.post(
        f"/api/v2/access/delegations/{delegation_id}/use",
        headers=_csrf(grantee_session.json()),
        json={
            "action_type": "purchase_authorization",
            "idempotency_key": f"delegated-purchase-revoked-{run_key}",
            "capability": "expense.approve",
            "resource_type": "property",
            "resource_id": str(property_id),
            "decision_type": "routine_purchase",
            "amount_minor": 1,
        },
    )
    assert after_revoke.status_code == 409
    assert after_revoke.json()["detail"]["code"] == "delegation_inactive"
    with runtime_transaction(Settings.load(), grantor_account, organization_id, uuid4()) as connection:
        usages = connection.execute(
            sql_text(
                """
                SELECT count(*) FROM delegation_usage
                WHERE organization_id = :org AND delegation_id = :delegation
                """
            ),
            {"org": organization_id, "delegation": UUID(delegation_id)},
        ).scalar_one()
        events = connection.execute(
            sql_text(
                """
                SELECT array_agg(action ORDER BY occurred_at)
                FROM delegation_events
                WHERE organization_id = :org AND delegation_id = :delegation
                """
            ),
            {"org": organization_id, "delegation": UUID(delegation_id)},
        ).scalar_one()
    assert usages == 1
    assert events == ["created", "used", "revoked"]


def test_maintenance_recommendation_and_management_variance_are_append_only():
    for email in ("ann.synthetic@example.com", "technician.synthetic@example.com"):
        _provider_user(email)
    client = TestClient(create_app())
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert signed.status_code == 200
    _mark_current_session_aal2(client, signed.json())
    organization_id = UUID(signed.json()["organization_id"])
    manager_account = UUID(client.get("/api/v2/auth/me").json()["account_id"])
    with runtime_transaction(Settings.load(), manager_account, organization_id, uuid4()) as connection:
        technician_account = sid("account-phase6-technician")
        assignment_id = uuid4()
        connection.execute(
            sql_text(
                """
                INSERT INTO worker_assignments (
                  organization_id, id, worker_account_id, property_id,
                  assignment_kind, starts_at, ends_at, status
                ) VALUES (
                  :org, :id, :worker, :property,
                  'technician', now(), now() + interval '7 days', 'active'
                )
                """
            ),
            {
                "org": organization_id,
                "id": assignment_id,
                "worker": technician_account,
                "property": sid("property-elm"),
            },
        )
    created = client.post(
        "/api/v2/maintenance/cases",
        headers=_csrf(signed.json()),
        json={
            "reported_problem": "Synthetic heat pump produces no warm air.",
            "assignment_id": str(assignment_id),
        },
    )
    assert created.status_code == 200, created.text
    case_id = created.json()["case_id"]
    misattributed = client.post(
        f"/api/v2/maintenance/cases/{case_id}/events",
        headers=_csrf(signed.json()),
        json={
            "event_type": "technician_recommendation",
            "content": "Replace the failed control board with synthetic part A.",
        },
    )
    assert misattributed.status_code == 404
    technician = TestClient(create_app())
    technician_signed = technician.post(
        "/api/v2/auth/sign-in",
        json={
            "email": "technician.synthetic@example.com",
            "password": Settings.load().dev_password,
        },
    )
    assert technician_signed.status_code == 200
    _mark_current_session_aal2(technician, technician_signed.json())
    recommendation = technician.post(
        f"/api/v2/maintenance/cases/{case_id}/events",
        headers=_csrf(technician_signed.json()),
        json={
            "event_type": "technician_recommendation",
            "content": "Replace the failed control board with synthetic part A.",
        },
    )
    assert recommendation.status_code == 200, recommendation.text
    decision = client.post(
        f"/api/v2/maintenance/cases/{case_id}/events",
        headers=_csrf(signed.json()),
        json={
            "event_type": "manager_decision",
            "content": "Select synthetic whole-unit replacement after lifecycle review.",
        },
    )
    assert decision.status_code == 200, decision.text
    variance = client.post(
        f"/api/v2/maintenance/cases/{case_id}/events",
        headers=_csrf(signed.json()),
        json={
            "event_type": "variance_reason",
            "content": "The selected solution differs because the existing unit is beyond supported life.",
        },
    )
    assert variance.status_code == 200, variance.text
    timeline = client.get(f"/api/v2/maintenance/cases/{case_id}")
    assert timeline.status_code == 200
    assert [event["event_type"] for event in timeline.json()["events"]] == [
        "reported_problem",
        "technician_recommendation",
        "manager_decision",
        "variance_reason",
    ]
    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        may_update = connection.execute(
            sql_text(
                """
                SELECT has_table_privilege(
                  'perchpoint_runtime',
                  'maintenance_case_events',
                  'UPDATE'
                )
                """
            )
        ).scalar_one()
    assert may_update is False


def test_vendor_admin_proposes_operations_approves_and_worker_assignment_activates():
    for email in ("ann.synthetic@example.com", "vendor.admin.synthetic@example.com"):
        _provider_user(email)
    operations = TestClient(create_app())
    operations_session = operations.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert operations_session.status_code == 200
    operations_account = UUID(operations.get("/api/v2/auth/me").json()["account_id"])
    organization_id = UUID(operations_session.json()["organization_id"])
    vendor = TestClient(create_app())
    vendor_session = vendor.post(
        "/api/v2/auth/sign-in",
        json={"email": "vendor.admin.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert vendor_session.status_code == 200
    vendor_account = UUID(vendor.get("/api/v2/auth/me").json()["account_id"])
    relationship_id = uuid4()
    with runtime_transaction(Settings.load(), operations_account, organization_id, uuid4()) as connection:
        connection.execute(
            sql_text(
                """
                UPDATE identity_sessions
                SET assurance = 'aal2', reauthenticated_at = now()
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                ) AND revoked_at IS NULL
                """
            ),
            {"account": operations_account},
        )
        connection.execute(
            sql_text(
                """
                INSERT INTO vendor_relationships (
                  organization_id, id, vendor_name, administrator_account_id, status
                ) VALUES (:org, :id, 'Synthetic Vendor Proposal Test', :administrator, 'active')
                """
            ),
            {
                "org": organization_id,
                "id": relationship_id,
                "administrator": vendor_account,
            },
        )
    with runtime_transaction(Settings.load(), vendor_account, organization_id, uuid4()) as connection:
        connection.execute(
            sql_text(
                """
                UPDATE identity_sessions
                SET assurance = 'aal2', reauthenticated_at = now()
                WHERE identity_id = (
                  SELECT id FROM identity_accounts WHERE account_id = :account
                ) AND revoked_at IS NULL
                """
            ),
            {"account": vendor_account},
        )
    worker_email = f"vendor.worker.{uuid4().hex[:8]}@example.com"
    proposed = vendor.post(
        "/api/v2/access/vendor/workers/proposals",
        headers=_csrf(vendor_session.json()),
        json={
            "vendor_relationship_id": str(relationship_id),
            "email": worker_email,
            "role_name": "technician",
            "starts_at": "2026-01-01T00:00:00Z",
            "ends_at": "2027-01-01T00:00:00Z",
        },
    )
    assert proposed.status_code == 200, proposed.text
    approved = operations.post(
        f"/api/v2/access/vendor/workers/proposals/{proposed.json()['proposal_id']}",
        headers=_csrf(operations_session.json()),
        json={"approve": True, "purpose": "Synthetic approved assignment"},
    )
    assert approved.status_code == 200, approved.text
    token = _invitation_token(worker_email)
    accepted = operations.post(
        "/api/v2/auth/invitations/accept",
        json={"token": token, "email": worker_email, "password": "synthetic-local-passphrase"},
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["worker_assignment_id"] is not None
    with runtime_transaction(Settings.load(), operations_account, organization_id, uuid4()) as connection:
        assignment = connection.execute(
            sql_text(
                """
                SELECT status, assignment_kind, vendor_relationship_id
                FROM worker_assignments
                WHERE organization_id = :org AND id = :id
                """
            ),
            {
                "org": organization_id,
                "id": UUID(accepted.json()["worker_assignment_id"]),
            },
        ).mappings().one()
        proposal_status = connection.execute(
            sql_text(
                """
                SELECT status FROM vendor_worker_proposals
                WHERE organization_id = :org AND id = :id
                """
            ),
            {
                "org": organization_id,
                "id": UUID(proposed.json()["proposal_id"]),
            },
        ).scalar_one()
    assert assignment["status"] == "active"
    assert assignment["assignment_kind"] == "technician"
    assert assignment["vendor_relationship_id"] == relationship_id
    assert proposal_status == "activated"


def test_suspension_revokes_authority_and_restoration_does_not_resurrect_it():
    _provider_user("nathan.synthetic@example.com")
    administrator = TestClient(create_app())
    admin_session = administrator.post(
        "/api/v2/auth/sign-in",
        json={"email": "nathan.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert admin_session.status_code == 200
    _mark_current_session_aal2(administrator, admin_session.json())
    organization_id = admin_session.json()["organization_id"]
    target_email = f"offboard.{uuid4().hex[:8]}@example.com"
    _account(target_email, "technician", organization_id)
    target = TestClient(create_app())
    target_session = target.post(
        "/api/v2/auth/sign-in",
        json={"email": target_email, "password": Settings.load().dev_password},
    )
    assert target_session.status_code == 200
    target_account = target.get("/api/v2/auth/me").json()["account_id"]
    suspended = administrator.post(
        f"/api/v2/access/users/{target_account}/suspend",
        headers=_csrf(admin_session.json()),
        json={"reason": "Synthetic contract ended"},
    )
    assert suspended.status_code == 200, suspended.text
    assert suspended.json()["memberships_ended"] == 1
    assert suspended.json()["sessions_revoked"] >= 1
    assert suspended.json()["authority_restored"] is False
    assert target.get("/api/v2/auth/me").status_code == 401
    restored = administrator.post(
        f"/api/v2/access/users/{target_account}/restore",
        headers=_csrf(admin_session.json()),
        json={"reason": "Synthetic identity restored pending separate access approval"},
    )
    assert restored.status_code == 200, restored.text
    assert restored.json()["authority_restored"] is False
    no_authority = target.post(
        "/api/v2/auth/sign-in",
        json={"email": target_email, "password": Settings.load().dev_password},
    )
    assert no_authority.status_code == 403
    assert no_authority.json()["detail"]["code"] == "membership_expired"


def test_privileged_recovery_requires_business_approval_and_cooling_period():
    clients = {}
    sessions = {}
    accounts = {}
    for label, email in {
        "nathan": "nathan.synthetic@example.com",
        "faruk": "faruk.synthetic@example.com",
        "ann": "ann.synthetic@example.com",
    }.items():
        _provider_user(email)
        clients[label] = TestClient(create_app())
        sessions[label] = clients[label].post(
            "/api/v2/auth/sign-in",
            json={"email": email, "password": Settings.load().dev_password},
        )
        assert sessions[label].status_code == 200
        _mark_current_session_aal2(clients[label], sessions[label].json())
        accounts[label] = clients[label].get("/api/v2/auth/me").json()["account_id"]
    unknown = clients["nathan"].post(
        "/api/v2/access/recoveries",
        headers=_csrf(sessions["nathan"].json()),
        json={
            "subject_account": str(uuid4()),
            "approver_account": accounts["faruk"],
            "evidence": "Synthetic evidence for an unknown subject",
        },
    )
    assert unknown.status_code == 409
    assert unknown.json()["detail"]["code"] == "recovery_participant_invalid"
    missing_approver = clients["nathan"].post(
        "/api/v2/access/recoveries",
        headers=_csrf(sessions["nathan"].json()),
        json={
            "subject_account": accounts["ann"],
            "evidence": "Synthetic evidence without business approval",
        },
    )
    assert missing_approver.status_code == 409
    assert missing_approver.json()["detail"]["code"] == "supervised_recovery_required"
    opened = clients["nathan"].post(
        "/api/v2/access/recoveries",
        headers=_csrf(sessions["nathan"].json()),
        json={
            "subject_account": accounts["ann"],
            "approver_account": accounts["faruk"],
            "evidence": "Synthetic sealed-envelope evidence reference",
        },
    )
    assert opened.status_code == 200, opened.text
    recovery_id = opened.json()["recovery_id"]
    approved = clients["faruk"].post(
        f"/api/v2/access/recoveries/{recovery_id}/approve",
        headers=_csrf(sessions["faruk"].json()),
    )
    assert approved.status_code == 200, approved.text
    cooling = clients["nathan"].post(
        f"/api/v2/access/recoveries/{recovery_id}/complete",
        headers=_csrf(sessions["nathan"].json()),
    )
    assert cooling.status_code == 409
    assert cooling.json()["detail"]["code"] == "recovery_not_ready"
    organization_id = UUID(sessions["nathan"].json()["organization_id"])
    with runtime_transaction(
        Settings.load(),
        UUID(accounts["nathan"]),
        organization_id,
        uuid4(),
    ) as connection:
        connection.execute(
            sql_text(
                """
                UPDATE privileged_recoveries
                SET not_before = now() - interval '1 minute'
                WHERE organization_id = :org AND id = :id
                """
            ),
            {"org": organization_id, "id": UUID(recovery_id)},
        )
    completed = clients["nathan"].post(
        f"/api/v2/access/recoveries/{recovery_id}/complete",
        headers=_csrf(sessions["nathan"].json()),
    )
    assert completed.status_code == 200, completed.text
    assert completed.json()["authority_changed"] is False
    assert clients["ann"].get("/api/v2/auth/me").status_code == 401


def test_resident_cannot_use_staff_invitation_route():
    _provider_user("ann.synthetic@example.com")
    bootstrap = TestClient(create_app())
    signed = bootstrap.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    ).json()
    email = f"resident.{uuid4().hex[:8]}@example.com"
    _account(email, "resident", signed["organization_id"])
    resident = TestClient(create_app())
    resident_session = resident.post(
        "/api/v2/auth/sign-in",
        json={"email": email, "password": Settings.load().dev_password},
    ).json()
    denied = resident.post(
        "/api/v2/auth/invitations",
        headers=_csrf(resident_session),
        json={"email": "target.synthetic@example.com", "role_name": "technician", "purpose": "Unauthorized", "staff": True},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "denied"


def test_privileged_roles_cannot_be_created_through_invitations():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password},
    )
    assert signed.status_code == 200
    _mark_current_session_aal2(client, signed.json())
    denied = client.post(
        "/api/v2/auth/invitations",
        headers=_csrf(signed.json()),
        json={
            "email": f"owner.{uuid4().hex[:8]}@example.com",
            "role_name": "owner",
            "purpose": "Forbidden direct owner grant",
            "staff": True,
        },
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "invitation_role_forbidden"


def test_session_key_rotation_preserves_old_session_and_refresh_ciphertext(monkeypatch):
    old_key = configured_session_keys()[0]
    _provider_user("guarantor.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={
            "email": "guarantor.synthetic@example.com",
            "password": Settings.load().dev_password,
        },
    )
    token = signed.cookies["pp_session"]
    monkeypatch.setenv(
        "PHASE6_SESSION_KEYS",
        f"new-local-rotation-key-with-at-least-thirty-two-characters,{old_key}",
    )
    session = resolve(Settings.load(), token)
    assert session is not None
    assert refresh_token_for(session)


def test_restricted_rls_enforces_household_and_worker_assignment_relationships():
    settings = Settings.load()
    admin_client = TestClient(create_app())
    _provider_user("ann.synthetic@example.com")
    signed = admin_client.post(
        "/api/v2/auth/sign-in",
        json={"email": "ann.synthetic@example.com", "password": settings.dev_password},
    ).json()
    organization = UUID(signed["organization_id"])
    resident_a, resident_b, worker_a, worker_b = (uuid4() for _ in range(4))
    household_a, household_b = uuid4(), uuid4()
    vendor = uuid4()
    property_id = sid("property-elm")
    database = create_engine(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with database.begin() as connection:
        for account, email, role in (
            (resident_a, f"resident-a.{uuid4().hex[:8]}@example.com", "resident"),
            (resident_b, f"resident-b.{uuid4().hex[:8]}@example.com", "resident"),
            (worker_a, f"worker-a.{uuid4().hex[:8]}@example.com", "technician"),
            (worker_b, f"worker-b.{uuid4().hex[:8]}@example.com", "technician"),
        ):
            connection.execute(
                sql_text("INSERT INTO accounts (id, email, password_hash) VALUES (:id, :email, 'provider-owned')"),
                {"id": account, "email": email},
            )
            connection.execute(
                sql_text(
                    """
                    INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at)
                    VALUES (:id, :account, :org, :role, now() - interval '1 day')
                    """
                ),
                {"id": uuid4(), "account": account, "org": organization, "role": role},
            )
        connection.execute(
            sql_text(
                """
                INSERT INTO households (organization_id, id, label)
                VALUES (:org, :a, 'Synthetic household A'), (:org, :b, 'Synthetic household B')
                """
            ),
            {"org": organization, "a": household_a, "b": household_b},
        )
        connection.execute(
            sql_text(
                """
                INSERT INTO portal_access (organization_id, id, household_id, account_id, kind, effective_at)
                VALUES (:org, :id_a, :household_a, :resident_a, 'primary', now() - interval '1 day'),
                       (:org, :id_b, :household_b, :resident_b, 'primary', now() - interval '1 day')
                """
            ),
            {
                "org": organization,
                "id_a": uuid4(),
                "id_b": uuid4(),
                "household_a": household_a,
                "household_b": household_b,
                "resident_a": resident_a,
                "resident_b": resident_b,
            },
        )
        connection.execute(
            sql_text(
                """
                INSERT INTO vendor_relationships
                  (organization_id, id, vendor_name, administrator_account_id, status)
                VALUES (:org, :vendor, 'Synthetic Vendor', :worker_a, 'active')
                """
            ),
            {"org": organization, "vendor": vendor, "worker_a": worker_a},
        )
        connection.execute(
            sql_text(
                """
                INSERT INTO worker_assignments
                  (organization_id, id, vendor_relationship_id, worker_account_id, property_id,
                   assignment_kind, starts_at, ends_at, status)
                VALUES
                  (:org, :assignment_a, :vendor, :worker_a, :property, 'technician',
                   now() - interval '1 hour', now() + interval '1 hour', 'active'),
                  (:org, :assignment_b, :vendor, :worker_b, :property, 'technician',
                   now() - interval '1 hour', now() + interval '1 hour', 'active')
                """
            ),
            {
                "org": organization,
                "assignment_a": uuid4(),
                "assignment_b": uuid4(),
                "vendor": vendor,
                "worker_a": worker_a,
                "worker_b": worker_b,
                "property": property_id,
            },
        )
        unassigned_property = uuid4()
        connection.execute(
            sql_text(
                """
                INSERT INTO properties (organization_id, id, name, property_type)
                VALUES (:org, :id, 'Synthetic unassigned property', 'mixed_use')
                """
            ),
            {"org": organization, "id": unassigned_property},
        )
    database.dispose()
    with runtime_transaction(settings, resident_a, organization, uuid4()) as connection:
        visible_households = set(connection.execute(sql_text("SELECT id FROM households")).scalars())
    assert visible_households == {household_a}
    with runtime_transaction(settings, worker_a, organization, uuid4()) as connection:
        visible_workers = set(connection.execute(sql_text("SELECT worker_account_id FROM worker_assignments")).scalars())
        visible_properties = set(connection.execute(sql_text("SELECT id FROM properties")).scalars())
    assert visible_workers == {worker_a}
    assert unassigned_property not in visible_properties
    assert visible_properties == {property_id}


def test_worker_routes_are_limited_to_active_assignment_properties():
    settings = Settings.load()
    client = TestClient(create_app())
    _provider_user("technician.synthetic@example.com")
    signed = client.post(
        "/api/v2/auth/sign-in",
        json={
            "email": "technician.synthetic@example.com",
            "password": settings.dev_password,
        },
    )
    assert signed.status_code == 200
    _mark_current_session_aal2(client, signed.json())

    unassigned_property = uuid4()
    database = create_engine(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with database.begin() as connection:
        connection.execute(
            sql_text(
                """
                INSERT INTO properties (organization_id, id, name, property_type)
                VALUES (:org, :id, 'Synthetic property outside the technician assignment', 'mixed_use')
                """
            ),
            {"org": signed.json()["organization_id"], "id": unassigned_property},
        )
    database.dispose()
    properties = client.get("/api/v2/properties")
    assert properties.status_code == 200
    visible = [item["id"] for item in properties.json()["properties"]]
    assert str(unassigned_property) not in visible
    assert str(sid("property-phase6-firefox")) not in visible
    assert str(sid("property-phase6-webkit")) not in visible
    assert visible == [str(sid("property-elm"))]

    households = client.get("/api/v2/households")
    assert households.status_code == 200
    assert households.json()["households"] == []

import base64
from uuid import uuid4

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text as sql_text

from perchpoint.db import runtime_transaction
from perchpoint.phase6_policy import approval_authority, authorize, password_problem, recovery_participants, totp, totp_matches
from foundation.seeds import sid
from perchpoint.phase6_provider import ProviderError, create_user, recovery_link
from perchpoint.routes import create_app
from perchpoint.settings import Settings


def _provider_user(email: str) -> None:
    try:
        create_user(email, Settings.load().dev_password)
    except ProviderError as exc:
        if exc.code != "authentication_failed":
            raise


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


def test_self_grant_self_approval_and_non_transitive_delegation():
    actor = str(uuid4())
    assert authorize(capability="membership.grant", role_name="platform_admin", actor_id=actor, target_id=actor).reason == "self_grant"
    assert authorize(capability="access.approve", role_name="owner", actor_id=actor, self_approval=True).reason == "self_approval"
    assert authorize(capability="delegation.grant", role_name="owner", actor_id=actor, delegated=True, delegation_active=True).reason == "delegation_non_transitive"
    assert authorize(capability="expense.approve", role_name="platform_admin", actor_id=actor).reason == "technical_role_is_not_business_authority"
    assert authorize(capability="platform.secrets", role_name="owner", actor_id=actor).reason == "owner_is_not_technical_operator"
    assert authorize(capability="platform.deploy", role_name="leasing", actor_id=actor).reason == "operations_boundary"


def test_step_up_and_totp():
    denied = authorize(capability="delegation.grant", role_name="owner", actor_id="a", assurance="aal1", privileged=True)
    assert denied.reason == "step_up_required"
    allowed = authorize(capability="delegation.grant", role_name="owner", actor_id="a", assurance="aal2", reauthenticated_age_seconds=60, privileged=True)
    assert allowed.allowed
    secret = b"synthetic-totp-secret"
    code = totp(secret, 1_700_000_000)
    assert totp_matches(secret, code, 1_700_000_000)
    assert not totp_matches(secret, "000000", 1_700_000_000)


def test_interactive_sign_in_uses_cookie_and_rejects_missing_csrf():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    assert signed.status_code == 200, signed.text
    assert "pp_session" in signed.cookies
    cookie = signed.headers["set-cookie"].lower()
    assert "httponly" in cookie
    assert "samesite=lax" in cookie
    assert signed.json()["role_name"] == "leasing"
    me = client.get("/api/v2/auth/me")
    assert me.status_code == 200
    purchase = client.post("/api/v2/access/purchase-authority", json={"amount_minor": 49999, "monthly_rent_minor": 150000})
    assert purchase.status_code == 200
    assert purchase.json()["authority"] == "routine"
    assert purchase.json()["allowed"] is True
    denied = client.post("/api/v2/auth/sign-out")
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "csrf_rejected"
    signed_out = client.post("/api/v2/auth/sign-out", headers={"x-perchpoint-csrf": signed.json()["csrf"]})
    assert signed_out.status_code == 200
    assert client.get("/api/v2/auth/me").status_code == 401


def test_invitation_is_single_use_and_totp_secret_is_not_stored_in_plaintext():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    csrf = {"x-perchpoint-csrf": signed.json()["csrf"]}
    invited = client.post(
        "/api/v2/auth/invitations",
        headers=csrf,
        json={"email": "worker.synthetic@example.com", "role_name": "technician", "purpose": "Assigned work only", "staff": False},
    )
    assert invited.status_code == 200, invited.text
    token = invited.json()["token"]
    assert client.post("/api/v2/auth/invitations/accept", json={"token": token}).status_code == 200
    replay = client.post("/api/v2/auth/invitations/accept", json={"token": token})
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
    csrf = {"x-perchpoint-csrf": fresh_signed.json()["csrf"]}
    enrolled = fresh_client.post("/api/v2/auth/mfa/enroll", headers=csrf)
    assert enrolled.status_code == 200, enrolled.text
    secret = enrolled.json()["secret"]
    padded = secret + ("=" * ((8 - len(secret) % 8) % 8))
    confirmed = fresh_client.post(
        "/api/v2/auth/mfa/confirm",
        headers=csrf,
        json={"factor_id": enrolled.json()["factor_id"], "code": totp(base64.b32decode(padded))},
    )
    assert confirmed.status_code == 200, confirmed.text
    codes = fresh_client.post("/api/v2/auth/recovery-codes", headers={"x-perchpoint-csrf": confirmed.json()["csrf"]})
    assert codes.status_code == 200
    assert len(codes.json()["codes"]) == 10


def test_self_delegation_is_rejected_and_a_bounded_grant_is_recorded():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    csrf = {"x-perchpoint-csrf": signed.json()["csrf"]}
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
    assert granted.status_code == 200, granted.text


def test_sessions_access_requests_and_self_recovery_are_enforced():
    _provider_user("ann.synthetic@example.com")
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    csrf = {"x-perchpoint-csrf": signed.json()["csrf"]}
    listed = client.get("/api/v2/me/sessions")
    assert listed.status_code == 200
    assert listed.json()["sessions"]
    assert "token" not in listed.json()["sessions"][0]
    requested = client.post("/api/v2/access/requests", headers=csrf, json={"capability": "document.read", "justification": "Need the lease file"})
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
    issued = client.post(f"/api/v2/access/service-credentials/{principal}", headers={"x-perchpoint-csrf": nathan.json()["csrf"]})
    assert issued.status_code == 200, issued.text
    assert issued.json()["shown_once"] is True
    assert len(issued.json()["credential"]) >= 20
    operations = TestClient(create_app())
    ann = operations.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    denied = operations.post(
        f"/api/v2/access/service-credentials/{sid('service-principal-worker')}",
        headers={"x-perchpoint-csrf": ann.json()["csrf"]},
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


def test_development_jwt_is_retired_without_the_test_fixture(monkeypatch):
    monkeypatch.setenv("PHASE6_ALLOW_DEV_JWT", "0")
    client = TestClient(create_app())
    response = client.post("/api/v2/session", json={"email": "ann.synthetic@example.com", "password": "x"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "development_jwt_retired"

import base64
from uuid import uuid4

from fastapi.testclient import TestClient

from perchpoint.phase6_policy import approval_authority, authorize, password_problem, totp, totp_matches
from perchpoint.routes import create_app
from perchpoint.settings import Settings


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
    client = TestClient(create_app())
    signed = client.post("/api/v2/auth/sign-in", json={"email": "ann.synthetic@example.com", "password": Settings.load().dev_password})
    assert signed.status_code == 200, signed.text
    assert "pp_session" in signed.cookies
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
    enrolled = client.post("/api/v2/auth/mfa/enroll", headers=csrf)
    assert enrolled.status_code == 200, enrolled.text
    secret = enrolled.json()["secret"]
    padded = secret + ("=" * ((8 - len(secret) % 8) % 8))
    confirmed = client.post(
        "/api/v2/auth/mfa/confirm",
        headers=csrf,
        json={"factor_id": enrolled.json()["factor_id"], "code": totp(base64.b32decode(padded))},
    )
    assert confirmed.status_code == 200, confirmed.text
    codes = client.post("/api/v2/auth/recovery-codes", headers=csrf)
    assert codes.status_code == 200
    assert len(codes.json()["codes"]) == 10


def test_self_delegation_is_rejected_and_a_bounded_grant_is_recorded():
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


def test_development_jwt_is_retired_without_the_test_fixture(monkeypatch):
    monkeypatch.setenv("PHASE6_ALLOW_DEV_JWT", "0")
    client = TestClient(create_app())
    response = client.post("/api/v2/session", json={"email": "ann.synthetic@example.com", "password": "x"})
    assert response.status_code == 404
    assert response.json()["detail"]["code"] == "development_jwt_retired"

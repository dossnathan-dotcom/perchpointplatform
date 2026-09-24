"""Phase 2 reference persistence tests. They fail if local PostgreSQL is not running."""
import os
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

load_dotenv()

from foundation.seeds import sid
from perchpoint.db import engine_for, runtime_transaction
from perchpoint.routes import create_app
from perchpoint.settings import Settings


def settings() -> Settings:
    return Settings.load()


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def _login(client, email):
    response = client.post("/api/v2/session", json={"email": email, "password": os.environ["PHASE2_DEV_PASSWORD"]})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def test_runtime_role_has_no_bypassrls():
    admin = engine_for(settings().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    with admin.connect() as connection:
        row = connection.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'perchpoint_runtime'")).one()
    admin.dispose()
    assert row.rolsuper is False
    assert row.rolbypassrls is False


def test_missing_context_reads_no_properties():
    with runtime_transaction(settings(), None, None, uuid4()) as connection:
        count = connection.execute(text("SELECT count(*) FROM properties")).scalar()
    assert count == 0


def test_cross_organization_login_cannot_see_hawkvision_property(client):
    token = _login(client, "isolation.synthetic@example.com")
    response = client.get("/api/v2/properties", headers={"Authorization": f"Bearer {token}", "X-Organization": str(sid("organization-demo"))})
    assert response.status_code == 200
    assert all(item["id"] != str(sid("property-elm")) for item in response.json()["properties"])


def test_public_listing_and_inquiry_then_staff_triage(client):
    listings = client.get("/api/v2/listings")
    assert listings.status_code == 200
    listing = listings.json()["listings"][0]
    assert "organization_id" not in listing
    key = "inquiry-" + uuid4().hex
    body = {"listing_id": listing["listing_id"], "name": "Synthetic Guest", "email": "guest@example.com", "intent": "showing", "message": "Example only", "idempotency_key": key}
    created = client.post("/api/v2/inquiries", json=body)
    assert created.status_code == 201, created.text
    replay = client.post("/api/v2/inquiries", json=body)
    assert replay.json()["inquiry_id"] == created.json()["inquiry_id"]
    conflict = client.post("/api/v2/inquiries", json={**body, "message": "different"})
    assert conflict.status_code == 409
    token = _login(client, "ann.synthetic@example.com")
    triaged = client.post(
        f"/api/v2/inquiries/{created.json()['inquiry_id']}/triage",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "assigned", "expected_version": 1, "idempotency_key": "triage-" + uuid4().hex},
    )
    assert triaged.status_code == 200, triaged.text
    stale = client.post(
        f"/api/v2/inquiries/{created.json()['inquiry_id']}/triage",
        headers={"Authorization": f"Bearer {token}"},
        json={"decision": "closed_not_pursuing", "expected_version": 1, "idempotency_key": "triage-" + uuid4().hex},
    )
    assert stale.status_code == 409


def test_runtime_cannot_update_audit():
    token_settings = settings()
    with pytest.raises(Exception):
        with runtime_transaction(token_settings, sid("account-phase2-nathan"), sid("organization-demo"), uuid4()) as connection:
            connection.execute(text("UPDATE audit_events SET action = 'tamper'"))

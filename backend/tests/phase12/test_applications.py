"""Phase 12 application collection, documents, and the screening boundary."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import runtime_transaction
from perchpoint.routes import create_app
from perchpoint.settings import Settings


def _login(client, email):
    response = client.post("/api/v2/session", json={"email": email, "password": os.environ["PHASE2_DEV_PASSWORD"]})
    assert response.status_code == 200, response.text
    return response.json(), {"Authorization": f"Bearer {response.json()['token']}"}


def _key(prefix):
    return f"{prefix}-{uuid4().hex}"


def _publish(client, headers, label):
    created = client.post("/api/v2/properties", headers=headers, json={"name": label, "property_type": "mixed_use", "idempotency_key": _key("prop")})
    building = client.post("/api/v2/buildings", headers=headers, json={"property_id": created.json()["id"], "name": "Primary", "allowed_uses": ["residential"], "idempotency_key": _key("bldg")})
    space = client.post("/api/v2/spaces", headers=headers, json={"property_id": created.json()["id"], "building_id": building.json()["id"], "label": label, "use": "residential", "square_feet": 900, "idempotency_key": _key("space")})
    listing = client.post("/api/v2/listings", headers=headers, json={"space_id": space.json()["id"], "property_name": label, "label": label, "use": "residential", "municipality": "Cincinnati", "state": "OH", "amount_minor": 140000, "currency": "USD", "idempotency_key": _key("listing")})
    for availability, day, name in (("coming_soon", "2026-10-01", "soon"), ("available", "2026-10-15", "open")):
        assert client.post("/api/v2/portfolio/availability", headers=headers, json={"space_id": space.json()["id"], "availability": availability, "effective_on": day, "confidence": "exact", "source": "manager_confirmation", "reason": "Synthetic application availability.", "idempotency_key": _key(name)}).status_code == 201
    assert client.post("/api/v2/portfolio/prices", headers=headers, json={"space_id": space.json()["id"], "amount_minor": 140000, "currency": "USD", "period": "monthly", "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": _key("price")}).status_code == 201
    assert client.post("/api/v2/portfolio/media", headers=headers, json={"space_id": space.json()["id"], "content": "JFIF-synthetic-front", "signature": "JFIF", "declared_mime": "image/jpeg", "alt_text": "Synthetic front of the home", "rights_state": "licensed", "idempotency_key": _key("media")}).status_code == 201
    slug = f"phase12-{uuid4().hex[:8]}"
    published = client.post("/api/v2/portfolio/snapshots", headers=headers, json={"listing_id": listing.json()["id"], "expected_version": 1, "public_slug": slug, "description": "EXAMPLE ONLY. Synthetic listing facts.", "idempotency_key": _key("publish")})
    assert client.post("/api/v2/discovery/project", headers=headers, json={"snapshot_id": published.json()["id"], "bedrooms": 2, "idempotency_key": _key("project")}).status_code == 201
    return slug


def _receipt(client, slug):
    response = client.post("/api/v2/public/leasing/inquiries", json={"name": "Casey Synthetic", "email": f"casey.{uuid4().hex[:8]}@example.com", "message": "Synthetic application interest.", "disclosure": True, "public_slug": slug, "idempotency_key": _key("intake")})
    assert response.status_code == 201, response.text
    return response.json()["receipt"]


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_application_submits_without_screening_or_payment(client):
    session, headers = _login(client, "ann.synthetic@example.com")
    slug = _publish(client, headers, f"A12 {uuid4().hex[:8]} Synthetic Court")
    receipt = _receipt(client, slug)
    denied = client.post("/api/v2/public/applications", json={"receipt": "missing-receipt", "disclosure": True, "idempotency_key": _key("missing")})
    assert denied.status_code == 400
    scored = client.post("/api/v2/public/applications", json={"receipt": receipt, "disclosure": True, "ssn": "000-00-0000", "idempotency_key": _key("ssn")})
    assert scored.status_code == 400
    key = _key("start")
    started = client.post("/api/v2/public/applications", json={"receipt": receipt, "disclosure": True, "preferred_name": "Casey", "legal_name": "Casey Synthetic", "email": "casey.synthetic@example.com", "idempotency_key": key})
    assert started.status_code == 200, started.text
    assert started.json()["state"] == "draft" and "ssn" not in started.text
    token = started.json()["capability"]
    replay = client.post("/api/v2/public/applications", json={"receipt": receipt, "disclosure": True, "preferred_name": "Casey", "legal_name": "Casey Synthetic", "email": "casey.synthetic@example.com", "idempotency_key": key})
    assert replay.json()["replayed"] is True and replay.json()["reference"] == started.json()["reference"]
    changed = client.post("/api/v2/public/applications", json={"receipt": receipt, "disclosure": True, "preferred_name": "Other", "legal_name": "Casey Synthetic", "email": "casey.synthetic@example.com", "idempotency_key": key})
    assert changed.status_code == 409
    saved = client.post("/api/v2/public/applications/answers", json={"capability": token, "field_code": "income_status", "field_value": "employed", "expected_version": 1})
    assert saved.status_code == 200, saved.text
    stale = client.post("/api/v2/public/applications/answers", json={"capability": token, "field_code": "income_status", "field_value": "employed", "expected_version": 1})
    assert stale.status_code == 409
    blocked = client.post("/api/v2/public/applications/answers", json={"capability": token, "field_code": "credit_score", "field_value": "700", "expected_version": saved.json()["version"]})
    assert blocked.status_code == 400
    malicious = client.post("/api/v2/public/applications/documents", json={"capability": token, "document_class": "income_evidence", "display_name": "../pay.txt", "content": "EICAR-synthetic", "magic": "JFIF"})
    assert malicious.status_code == 200 and malicious.json()["scan_state"] == "rejected"
    document = client.post("/api/v2/public/applications/documents", json={"capability": token, "document_class": "income_evidence", "display_name": "pay.txt", "content": "JFIF-synthetic-pay", "magic": "JFIF"})
    assert document.status_code == 200 and document.json()["scan_state"] == "clean"
    minor = client.post("/api/v2/public/applications/invitations", json={"capability": token, "role_name": "minor_occupant", "destination_email": "minor@example.com"})
    assert minor.status_code == 400
    invited = client.post("/api/v2/public/applications/invitations", json={"capability": token, "role_name": "co_applicant", "destination_email": "co.synthetic@example.com"})
    assert invited.status_code == 200 and "invitation" in invited.json()
    unattested = client.post("/api/v2/public/applications/submit", json={"capability": token, "idempotency_key": _key("submit"), "expected_version": saved.json()["version"], "attestation": False})
    assert unattested.status_code == 400
    submit_key = _key("submit")
    submitted = client.post("/api/v2/public/applications/submit", json={"capability": token, "idempotency_key": submit_key, "expected_version": saved.json()["version"], "attestation": True})
    assert submitted.status_code == 200, submitted.text
    assert submitted.json()["state"] == "submitted" and submitted.json()["snapshot_hash"]
    again = client.post("/api/v2/public/applications/submit", json={"capability": token, "idempotency_key": submit_key, "expected_version": saved.json()["version"], "attestation": True})
    assert again.json()["replayed"] is True
    handed = client.post("/api/v2/leasing/applications/handoff", headers=headers, json={"reference": submitted.json()["reference"]})
    assert handed.status_code == 200 and handed.json()["state"] == "ready_for_screening"
    requested = client.post("/api/v2/leasing/applications/requests", headers=headers, json={"reference": submitted.json()["reference"], "field_code": "rental_history"})
    assert requested.status_code == 200
    arbitrary = client.post("/api/v2/leasing/applications/requests", headers=headers, json={"reference": submitted.json()["reference"], "field_code": "ssn"})
    assert arbitrary.status_code == 400
    _, isolation_headers = _login(client, "isolation.synthetic@example.com")
    hidden = client.post("/api/v2/leasing/applications/handoff", headers=isolation_headers, json={"reference": submitted.json()["reference"]})
    assert hidden.status_code == 403
    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        assert connection.execute(text("SELECT count(*) FROM applications")).scalar_one() == 0
        assert connection.execute(text("SELECT to_regclass('public.screening_decisions')")).scalar_one() is None
    assert session["organization_id"]

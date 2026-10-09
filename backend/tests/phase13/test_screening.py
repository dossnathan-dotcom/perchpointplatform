"""Phase 13 screening decisions stay human and provider-neutral."""
import hashlib
import hmac
import json
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
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _key(prefix):
    return f"{prefix}-{uuid4().hex}"


def _ready_application(client, headers):
    label = f"A13 {uuid4().hex[:8]} Synthetic Court"
    created = client.post("/api/v2/properties", headers=headers, json={"name": label, "property_type": "mixed_use", "idempotency_key": _key("prop")})
    building = client.post("/api/v2/buildings", headers=headers, json={"property_id": created.json()["id"], "name": "Primary", "allowed_uses": ["residential"], "idempotency_key": _key("bldg")})
    space = client.post("/api/v2/spaces", headers=headers, json={"property_id": created.json()["id"], "building_id": building.json()["id"], "label": label, "use": "residential", "square_feet": 900, "idempotency_key": _key("space")})
    listing = client.post("/api/v2/listings", headers=headers, json={"space_id": space.json()["id"], "property_name": label, "label": label, "use": "residential", "municipality": "Cincinnati", "state": "OH", "amount_minor": 140000, "currency": "USD", "idempotency_key": _key("listing")})
    for availability, day, name in (("coming_soon", "2026-10-01", "soon"), ("available", "2026-10-15", "open")):
        assert client.post("/api/v2/portfolio/availability", headers=headers, json={"space_id": space.json()["id"], "availability": availability, "effective_on": day, "confidence": "exact", "source": "manager_confirmation", "reason": "Synthetic screening availability.", "idempotency_key": _key(name)}).status_code == 201
    assert client.post("/api/v2/portfolio/prices", headers=headers, json={"space_id": space.json()["id"], "amount_minor": 140000, "currency": "USD", "period": "monthly", "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": _key("price")}).status_code == 201
    assert client.post("/api/v2/portfolio/media", headers=headers, json={"space_id": space.json()["id"], "content": "JFIF-synthetic-front", "signature": "JFIF", "declared_mime": "image/jpeg", "alt_text": "Synthetic front of the home", "rights_state": "licensed", "idempotency_key": _key("media")}).status_code == 201
    slug = f"phase13-{uuid4().hex[:8]}"
    published = client.post("/api/v2/portfolio/snapshots", headers=headers, json={"listing_id": listing.json()["id"], "expected_version": 1, "public_slug": slug, "description": "EXAMPLE ONLY. Synthetic listing facts.", "idempotency_key": _key("publish")})
    assert client.post("/api/v2/discovery/project", headers=headers, json={"snapshot_id": published.json()["id"], "bedrooms": 2, "idempotency_key": _key("project")}).status_code == 201
    inquiry = client.post("/api/v2/public/leasing/inquiries", json={"name": "Casey Synthetic", "email": f"casey.{uuid4().hex[:8]}@example.com", "message": "Synthetic screening interest.", "disclosure": True, "public_slug": slug, "idempotency_key": _key("intake")})
    started = client.post("/api/v2/public/applications", json={"receipt": inquiry.json()["receipt"], "disclosure": True, "preferred_name": "Casey", "legal_name": "Casey Synthetic", "email": "casey.synthetic@example.com", "idempotency_key": _key("start")})
    token = started.json()["capability"]
    saved = client.post("/api/v2/public/applications/answers", json={"capability": token, "field_code": "income_status", "field_value": "employed", "expected_version": 1})
    assert client.post("/api/v2/public/applications/documents", json={"capability": token, "document_class": "income_evidence", "display_name": "pay.txt", "content": "JFIF-synthetic-pay", "magic": "JFIF"}).status_code == 200
    submitted = client.post("/api/v2/public/applications/submit", json={"capability": token, "idempotency_key": _key("submit"), "expected_version": saved.json()["version"], "attestation": True})
    return submitted.json()["reference"]


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_human_decision_uses_fake_evidence_and_does_not_create_a_lease(client):
    headers = _login(client, "ann.synthetic@example.com")
    application_reference = _ready_application(client, headers)
    too_early = client.post("/api/v2/leasing/screening/cases", headers=headers, json={"application_reference": application_reference, "idempotency_key": _key("early")})
    assert too_early.status_code == 400
    assert client.post("/api/v2/leasing/applications/handoff", headers=headers, json={"reference": application_reference}).status_code == 200
    key = _key("case")
    opened = client.post("/api/v2/leasing/screening/cases", headers=headers, json={"application_reference": application_reference, "idempotency_key": key})
    assert opened.status_code == 200, opened.text
    token = opened.json()["capability"]
    replay = client.post("/api/v2/leasing/screening/cases", headers=headers, json={"application_reference": application_reference, "idempotency_key": key})
    assert replay.json()["replayed"] is True and replay.json()["reference"] == opened.json()["reference"]
    criminal = client.post("/api/v2/public/screening/orders", json={"capability": token, "product": "criminal", "idempotency_key": _key("crime")})
    assert criminal.status_code == 400
    blocked = client.post("/api/v2/public/screening/orders", json={"capability": token, "product": "credit", "idempotency_key": _key("credit")})
    assert blocked.status_code == 409
    assert client.post("/api/v2/public/screening/authorization", json={"capability": token}).status_code == 200
    order_key = _key("credit")
    ordered = client.post("/api/v2/public/screening/orders", json={"capability": token, "product": "credit", "idempotency_key": order_key})
    assert ordered.status_code == 200, ordered.text
    again = client.post("/api/v2/public/screening/orders", json={"capability": token, "product": "credit", "idempotency_key": order_key})
    assert again.json()["replayed"] is True
    body = json.dumps({"coverage": "complete"}).encode()
    signature = hmac.new(os.environ["PHASE2_WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest()
    forged = client.post("/api/v2/public/screening/results", content=body, headers={"x-perchpoint-capability": token, "x-perchpoint-coverage": "complete", "x-perchpoint-signature": "forged"})
    assert forged.status_code == 400
    resulted = client.post("/api/v2/public/screening/results", content=body, headers={"x-perchpoint-capability": token, "x-perchpoint-coverage": "complete", "x-perchpoint-signature": signature, "content-type": "application/json"})
    assert resulted.status_code == 200, resulted.text
    assert resulted.json()["state"] == "ready_for_review"
    unconfirmed = client.post("/api/v2/leasing/screening/decisions", headers=headers, json={"reference": opened.json()["reference"], "outcome": "denied", "human_confirmed": False})
    assert unconfirmed.status_code == 400
    decided = client.post("/api/v2/leasing/screening/decisions", headers=headers, json={"reference": opened.json()["reference"], "outcome": "denied", "human_confirmed": True})
    assert decided.status_code == 200, decided.text
    assert decided.json()["notice_kind"] == "adverse_action" and decided.json()["human_confirmed"] is True
    handed = client.post("/api/v2/leasing/screening/handoff", headers=headers, json={"reference": opened.json()["reference"]})
    assert handed.status_code == 409
    disputed = client.post("/api/v2/leasing/screening/disputes", headers=headers, json={"reference": opened.json()["reference"], "dispute_kind": "identity"})
    assert disputed.status_code == 200
    arrest = client.post("/api/v2/leasing/screening/criminal-safeguard", headers=headers, json={"record_kind": "arrest_only"})
    assert arrest.status_code == 400
    individualized = client.post("/api/v2/leasing/screening/criminal-safeguard", headers=headers, json={"record_kind": "test_only_individualized"})
    assert individualized.status_code == 200 and individualized.json()["ordered"] is False
    isolation = _login(client, "isolation.synthetic@example.com")
    hidden = client.post("/api/v2/leasing/screening/decisions", headers=isolation, json={"reference": opened.json()["reference"], "outcome": "approved", "human_confirmed": True})
    assert hidden.status_code == 403
    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        assert connection.execute(text("SELECT count(*) FROM screening_cases")).scalar_one() == 0
        assert connection.execute(text("SELECT to_regclass('public.leases')")).scalar_one() is None
        assert connection.execute(text("SELECT count(*) FROM screening_orders WHERE product = 'criminal'")).scalar_one() == 0

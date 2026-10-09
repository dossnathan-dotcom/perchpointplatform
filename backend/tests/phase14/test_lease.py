"""Phase 14 activates a resident only after an approved handoff, human package approval, and fake execution."""
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
    label = f"A14 {uuid4().hex[:8]} Synthetic Court"
    created = client.post("/api/v2/properties", headers=headers, json={"name": label, "property_type": "mixed_use", "idempotency_key": _key("prop")})
    building = client.post("/api/v2/buildings", headers=headers, json={"property_id": created.json()["id"], "name": "Primary", "allowed_uses": ["residential"], "idempotency_key": _key("bldg")})
    space = client.post("/api/v2/spaces", headers=headers, json={"property_id": created.json()["id"], "building_id": building.json()["id"], "label": label, "use": "residential", "square_feet": 900, "idempotency_key": _key("space")})
    listing = client.post("/api/v2/listings", headers=headers, json={"space_id": space.json()["id"], "property_name": label, "label": label, "use": "residential", "municipality": "Cincinnati", "state": "OH", "amount_minor": 140000, "currency": "USD", "idempotency_key": _key("listing")})
    for availability, day, name in (("coming_soon", "2026-10-01", "soon"), ("available", "2026-10-15", "open")):
        assert client.post("/api/v2/portfolio/availability", headers=headers, json={"space_id": space.json()["id"], "availability": availability, "effective_on": day, "confidence": "exact", "source": "manager_confirmation", "reason": "Synthetic lease availability.", "idempotency_key": _key(name)}).status_code == 201
    assert client.post("/api/v2/portfolio/prices", headers=headers, json={"space_id": space.json()["id"], "amount_minor": 140000, "currency": "USD", "period": "monthly", "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": _key("price")}).status_code == 201
    assert client.post("/api/v2/portfolio/media", headers=headers, json={"space_id": space.json()["id"], "content": "JFIF-synthetic-front", "signature": "JFIF", "declared_mime": "image/jpeg", "alt_text": "Synthetic front of the home", "rights_state": "licensed", "idempotency_key": _key("media")}).status_code == 201
    slug = f"phase14-{uuid4().hex[:8]}"
    published = client.post("/api/v2/portfolio/snapshots", headers=headers, json={"listing_id": listing.json()["id"], "expected_version": 1, "public_slug": slug, "description": "EXAMPLE ONLY. Synthetic listing facts.", "idempotency_key": _key("publish")})
    assert client.post("/api/v2/discovery/project", headers=headers, json={"snapshot_id": published.json()["id"], "bedrooms": 2, "idempotency_key": _key("project")}).status_code == 201
    inquiry = client.post("/api/v2/public/leasing/inquiries", json={"name": "Casey Synthetic", "email": f"casey.{uuid4().hex[:8]}@example.com", "message": "Synthetic lease interest.", "disclosure": True, "public_slug": slug, "idempotency_key": _key("intake")})
    started = client.post("/api/v2/public/applications", json={"receipt": inquiry.json()["receipt"], "disclosure": True, "preferred_name": "Casey", "legal_name": "Casey Synthetic", "email": "casey.synthetic@example.com", "idempotency_key": _key("start")})
    token = started.json()["capability"]
    saved = client.post("/api/v2/public/applications/answers", json={"capability": token, "field_code": "income_status", "field_value": "employed", "expected_version": 1})
    assert client.post("/api/v2/public/applications/documents", json={"capability": token, "document_class": "income_evidence", "display_name": "pay.txt", "content": "JFIF-synthetic-pay", "magic": "JFIF"}).status_code == 200
    submitted = client.post("/api/v2/public/applications/submit", json={"capability": token, "idempotency_key": _key("submit"), "expected_version": saved.json()["version"], "attestation": True})
    return submitted.json()["reference"]


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_activation_requires_an_approved_handoff_and_does_not_collect_money(client):
    headers = _login(client, "ann.synthetic@example.com")
    application_reference = _ready_application(client, headers)
    assert client.post("/api/v2/leasing/applications/handoff", headers=headers, json={"reference": application_reference}).status_code == 200
    opened = client.post("/api/v2/leasing/screening/cases", headers=headers, json={"application_reference": application_reference, "idempotency_key": _key("case")})
    assert opened.status_code == 200, opened.text
    token = opened.json()["capability"]
    screening_reference = opened.json()["reference"]
    blocked = client.post("/api/v2/leasing/leases/deals", headers=headers, json={"screening_reference": screening_reference, "idempotency_key": _key("early")})
    assert blocked.status_code == 409
    assert client.post("/api/v2/public/screening/authorization", json={"capability": token}).status_code == 200
    assert client.post("/api/v2/public/screening/orders", json={"capability": token, "product": "credit", "idempotency_key": _key("credit")}).status_code == 200
    body = json.dumps({"coverage": "complete"}).encode()
    signature = hmac.new(os.environ["PHASE2_WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest()
    resulted = client.post("/api/v2/public/screening/results", content=body, headers={"x-perchpoint-capability": token, "x-perchpoint-coverage": "complete", "x-perchpoint-signature": signature, "content-type": "application/json"})
    assert resulted.status_code == 200, resulted.text
    decided = client.post("/api/v2/leasing/screening/decisions", headers=headers, json={"reference": screening_reference, "outcome": "approved", "human_confirmed": True})
    assert decided.status_code == 200, decided.text
    handed = client.post("/api/v2/leasing/screening/handoff", headers=headers, json={"reference": screening_reference})
    assert handed.status_code == 200, handed.text
    deal_key = _key("deal")
    deal = client.post("/api/v2/leasing/leases/deals", headers=headers, json={"screening_reference": screening_reference, "idempotency_key": deal_key})
    assert deal.status_code == 200, deal.text
    capability = deal.json()["capability"]
    replay = client.post("/api/v2/leasing/leases/deals", headers=headers, json={"screening_reference": screening_reference, "idempotency_key": deal_key})
    assert replay.json()["replayed"] is True
    unconfirmed = client.post("/api/v2/leasing/leases/approvals", headers=headers, json={"reference": deal.json()["reference"], "human_confirmed": False})
    assert unconfirmed.status_code == 400
    approved = client.post("/api/v2/leasing/leases/approvals", headers=headers, json={"reference": deal.json()["reference"], "human_confirmed": True})
    assert approved.status_code == 200 and approved.json()["human_confirmed"] is True
    signed = client.post("/api/v2/public/leases/signatures", json={"capability": capability, "idempotency_key": _key("sign")})
    assert signed.status_code == 200, signed.text
    event = json.dumps({"coverage": "complete"}).encode()
    event_signature = hmac.new(os.environ["PHASE2_WEBHOOK_SECRET"].encode(), event, hashlib.sha256).hexdigest()
    forged = client.post("/api/v2/public/leases/signatures/events", content=event, headers={"x-perchpoint-capability": capability, "x-perchpoint-signature": "forged"})
    assert forged.status_code == 400
    live = json.dumps({"provider": "live"}).encode()
    live_signature = hmac.new(os.environ["PHASE2_WEBHOOK_SECRET"].encode(), live, hashlib.sha256).hexdigest()
    rejected = client.post("/api/v2/public/leases/signatures/events", content=live, headers={"x-perchpoint-capability": capability, "x-perchpoint-signature": live_signature})
    assert rejected.status_code == 400
    executed = client.post("/api/v2/public/leases/signatures/events", content=event, headers={"x-perchpoint-capability": capability, "x-perchpoint-signature": event_signature, "content-type": "application/json"})
    assert executed.status_code == 200 and executed.json()["state"] == "executed"
    too_soon = client.post("/api/v2/leasing/leases/activations", headers=headers, json={"reference": deal.json()["reference"], "idempotency_key": _key("early-activate")})
    assert too_soon.status_code == 409
    deposit = client.post("/api/v2/leasing/leases/deposits", headers=headers, json={"reference": deal.json()["reference"]})
    assert deposit.status_code == 200 and deposit.json()["ledger_posted"] is False
    assert client.post("/api/v2/leasing/leases/payments", headers=headers).status_code == 400
    activation_key = _key("activate")
    activated = client.post("/api/v2/leasing/leases/activations", headers=headers, json={"reference": deal.json()["reference"], "idempotency_key": activation_key})
    assert activated.status_code == 200, activated.text
    assert activated.json()["state"] == "activated"
    again = client.post("/api/v2/leasing/leases/activations", headers=headers, json={"reference": deal.json()["reference"], "idempotency_key": activation_key})
    assert again.json()["replayed"] is True
    isolation = _login(client, "isolation.synthetic@example.com")
    hidden = client.post("/api/v2/leasing/leases/activations", headers=isolation, json={"reference": deal.json()["reference"], "idempotency_key": _key("other")})
    assert hidden.status_code == 403
    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        assert connection.execute(text("SELECT count(*) FROM lease_deals")).scalar_one() == 0
        assert connection.execute(text("SELECT to_regclass('public.ledger_postings')")).scalar_one() is None
        assert connection.execute(text("SELECT to_regclass('public.resident_portal_sessions')")).scalar_one() is None

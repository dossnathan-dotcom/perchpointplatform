"""Phase 15 opens a household portal only after Phase 14 activation and does not collect money."""
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
    label = f"A15 {uuid4().hex[:8]} Synthetic Court"
    created = client.post("/api/v2/properties", headers=headers, json={"name": label, "property_type": "mixed_use", "idempotency_key": _key("prop")})
    building = client.post("/api/v2/buildings", headers=headers, json={"property_id": created.json()["id"], "name": "Primary", "allowed_uses": ["residential"], "idempotency_key": _key("bldg")})
    space = client.post("/api/v2/spaces", headers=headers, json={"property_id": created.json()["id"], "building_id": building.json()["id"], "label": label, "use": "residential", "square_feet": 900, "idempotency_key": _key("space")})
    listing = client.post("/api/v2/listings", headers=headers, json={"space_id": space.json()["id"], "property_name": label, "label": label, "use": "residential", "municipality": "Cincinnati", "state": "OH", "amount_minor": 140000, "currency": "USD", "idempotency_key": _key("listing")})
    for availability, day, name in (("coming_soon", "2026-10-01", "soon"), ("available", "2026-10-15", "open")):
        assert client.post("/api/v2/portfolio/availability", headers=headers, json={"space_id": space.json()["id"], "availability": availability, "effective_on": day, "confidence": "exact", "source": "manager_confirmation", "reason": "Synthetic portal availability.", "idempotency_key": _key(name)}).status_code == 201
    assert client.post("/api/v2/portfolio/prices", headers=headers, json={"space_id": space.json()["id"], "amount_minor": 140000, "currency": "USD", "period": "monthly", "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": _key("price")}).status_code == 201
    assert client.post("/api/v2/portfolio/media", headers=headers, json={"space_id": space.json()["id"], "content": "JFIF-synthetic-front", "signature": "JFIF", "declared_mime": "image/jpeg", "alt_text": "Synthetic front of the home", "rights_state": "licensed", "idempotency_key": _key("media")}).status_code == 201
    slug = f"phase15-{uuid4().hex[:8]}"
    published = client.post("/api/v2/portfolio/snapshots", headers=headers, json={"listing_id": listing.json()["id"], "expected_version": 1, "public_slug": slug, "description": "EXAMPLE ONLY. Synthetic listing facts.", "idempotency_key": _key("publish")})
    assert client.post("/api/v2/discovery/project", headers=headers, json={"snapshot_id": published.json()["id"], "bedrooms": 2, "idempotency_key": _key("project")}).status_code == 201
    inquiry = client.post("/api/v2/public/leasing/inquiries", json={"name": "Casey Synthetic", "email": f"casey.{uuid4().hex[:8]}@example.com", "message": "Synthetic portal interest.", "disclosure": True, "public_slug": slug, "idempotency_key": _key("intake")})
    started = client.post("/api/v2/public/applications", json={"receipt": inquiry.json()["receipt"], "disclosure": True, "preferred_name": "Casey", "legal_name": "Casey Synthetic", "email": "casey.synthetic@example.com", "idempotency_key": _key("start")})
    token = started.json()["capability"]
    saved = client.post("/api/v2/public/applications/answers", json={"capability": token, "field_code": "income_status", "field_value": "employed", "expected_version": 1})
    assert client.post("/api/v2/public/applications/documents", json={"capability": token, "document_class": "income_evidence", "display_name": "pay.txt", "content": "JFIF-synthetic-pay", "magic": "JFIF"}).status_code == 200
    submitted = client.post("/api/v2/public/applications/submit", json={"capability": token, "idempotency_key": _key("submit"), "expected_version": saved.json()["version"], "attestation": True})
    return submitted.json()["reference"]


def _activate(client, headers):
    application_reference = _ready_application(client, headers)
    assert client.post("/api/v2/leasing/applications/handoff", headers=headers, json={"reference": application_reference}).status_code == 200
    opened = client.post("/api/v2/leasing/screening/cases", headers=headers, json={"application_reference": application_reference, "idempotency_key": _key("case")})
    assert opened.status_code == 200, opened.text
    token = opened.json()["capability"]
    screening_reference = opened.json()["reference"]
    assert client.post("/api/v2/public/screening/authorization", json={"capability": token}).status_code == 200
    assert client.post("/api/v2/public/screening/orders", json={"capability": token, "product": "credit", "idempotency_key": _key("credit")}).status_code == 200
    body = json.dumps({"coverage": "complete"}).encode()
    signature = hmac.new(os.environ["PHASE2_WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest()
    assert client.post("/api/v2/public/screening/results", content=body, headers={"x-perchpoint-capability": token, "x-perchpoint-coverage": "complete", "x-perchpoint-signature": signature, "content-type": "application/json"}).status_code == 200
    assert client.post("/api/v2/leasing/screening/decisions", headers=headers, json={"reference": screening_reference, "outcome": "approved", "human_confirmed": True}).status_code == 200
    assert client.post("/api/v2/leasing/screening/handoff", headers=headers, json={"reference": screening_reference}).status_code == 200
    deal = client.post("/api/v2/leasing/leases/deals", headers=headers, json={"screening_reference": screening_reference, "idempotency_key": _key("deal")})
    assert deal.status_code == 200, deal.text
    capability = deal.json()["capability"]
    reference = deal.json()["reference"]
    assert client.post("/api/v2/leasing/portal/memberships", headers=headers, json={"reference": reference, "idempotency_key": _key("too-soon")}).status_code == 409
    assert client.post("/api/v2/leasing/leases/approvals", headers=headers, json={"reference": reference, "human_confirmed": True}).status_code == 200
    assert client.post("/api/v2/public/leases/signatures", json={"capability": capability, "idempotency_key": _key("sign")}).status_code == 200
    event = json.dumps({"coverage": "complete"}).encode()
    event_signature = hmac.new(os.environ["PHASE2_WEBHOOK_SECRET"].encode(), event, hashlib.sha256).hexdigest()
    assert client.post("/api/v2/public/leases/signatures/events", content=event, headers={"x-perchpoint-capability": capability, "x-perchpoint-signature": event_signature, "content-type": "application/json"}).status_code == 200
    assert client.post("/api/v2/leasing/leases/deposits", headers=headers, json={"reference": reference}).json()["ledger_posted"] is False
    assert client.post("/api/v2/leasing/leases/payments", headers=headers).status_code == 400
    activated = client.post("/api/v2/leasing/leases/activations", headers=headers, json={"reference": reference, "idempotency_key": _key("activate")})
    assert activated.status_code == 200, activated.text
    return reference


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_portal_requires_activation_and_does_not_open_later_domains(client):
    headers = _login(client, "ann.synthetic@example.com")
    lease_reference = _activate(client, headers)
    portal_key = _key("portal")
    opened = client.post("/api/v2/leasing/portal/memberships", headers=headers, json={"reference": lease_reference, "idempotency_key": portal_key})
    assert opened.status_code == 200, opened.text
    assert opened.json()["state"] == "pending"
    capability = opened.json()["capability"]
    portal_reference = opened.json()["reference"]
    replay = client.post("/api/v2/leasing/portal/memberships", headers=headers, json={"reference": lease_reference, "idempotency_key": portal_key})
    assert replay.json()["replayed"] is True
    assert "capability" not in replay.json()
    duplicate = client.post("/api/v2/leasing/portal/memberships", headers=headers, json={"reference": lease_reference, "idempotency_key": _key("again")})
    assert duplicate.status_code == 409
    forged = client.post("/api/v2/public/portal/invitations", json={"capability": "not-a-real-token", "idempotency_key": _key("forged")})
    assert forged.status_code == 400
    too_early = client.post("/api/v2/leasing/portal/documents", headers=headers, json={"reference": portal_reference})
    assert too_early.status_code == 409
    accept_key = _key("accept")
    accepted = client.post("/api/v2/public/portal/invitations", json={"capability": capability, "idempotency_key": accept_key})
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["state"] == "active" and accepted.json()["replayed"] is False
    again = client.post("/api/v2/public/portal/invitations", json={"capability": capability, "idempotency_key": accept_key})
    assert again.json()["replayed"] is True
    home = client.post("/api/v2/leasing/portal/home", headers=headers, json={"reference": portal_reference})
    assert home.status_code == 200, home.text
    assert home.json()["ledger_posted"] is False
    assert all(item["demo_preview"] is True and item["authoritative"] is False for item in home.json()["previews"])
    document = client.post("/api/v2/leasing/portal/documents", headers=headers, json={"reference": portal_reference})
    assert document.status_code == 200, document.text
    assert "SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION" in document.json()["body"]
    assert document.headers["cache-control"] == "no-store"
    preference = client.post("/api/v2/leasing/portal/preferences", headers=headers, json={"reference": portal_reference, "channel": "portal", "quiet_hours": True})
    assert preference.status_code == 200 and preference.json()["version"] == 1
    requested = client.post("/api/v2/leasing/portal/requests", headers=headers, json={"reference": portal_reference, "request_kind": "profile", "requested_delta": "preferred name Casey"})
    assert requested.status_code == 200, requested.text
    assert requested.json()["canonical_changed"] is False and requested.json()["lease_state"] == "activated"
    hidden = client.post("/api/v2/leasing/portal/requests", headers=headers, json={"reference": portal_reference, "request_kind": "accommodation", "requested_delta": "a quieter entry path"})
    assert hidden.status_code == 200
    blocked = client.post("/api/v2/leasing/portal/configuration", headers=headers, json={"family_code": "residential", "clause_code": "overlap", "human_confirmed": True})
    assert blocked.status_code == 400
    published = client.post("/api/v2/leasing/portal/configuration", headers=headers, json={"family_code": "residential", "clause_code": "sample-term", "human_confirmed": True})
    assert published.status_code == 200 and published.json()["edited_in_place"] is False
    first_hash = published.json()["content_hash"]
    successor = client.post("/api/v2/leasing/portal/configuration", headers=headers, json={"family_code": "residential", "clause_code": "sample-term-next", "human_confirmed": True})
    assert successor.json()["version"] == 2 and successor.json()["content_hash"] != first_hash
    secret = client.post("/api/v2/leasing/portal/manifest", headers=headers, json={"display_name": "Example Homes", "extra": {"secret": "not-stored"}})
    assert secret.status_code == 400
    manifest = client.post("/api/v2/leasing/portal/manifest", headers=headers, json={"display_name": "Example Homes"})
    assert manifest.status_code == 200 and manifest.json()["real_values_activated"] is False
    assert client.post("/api/v2/leasing/portal/payments", headers=headers).status_code == 400
    assert client.post("/api/v2/leasing/portal/maintenance", headers=headers).status_code == 400
    assert client.post("/api/v2/leasing/portal/messages", headers=headers).status_code == 400
    resident = _login(client, "resident.synthetic@example.com")
    assert client.post("/api/v2/leasing/portal/home", headers=resident, json={"reference": portal_reference}).status_code == 403
    isolation = _login(client, "isolation.synthetic@example.com")
    assert client.post("/api/v2/leasing/portal/home", headers=isolation, json={"reference": portal_reference}).status_code == 403
    revoked = client.post("/api/v2/leasing/portal/revocations", headers=headers, json={"reference": portal_reference})
    assert revoked.status_code == 200 and revoked.json()["state"] == "revoked"
    denied = client.post("/api/v2/leasing/portal/documents", headers=headers, json={"reference": portal_reference})
    assert denied.status_code == 409
    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        assert connection.execute(text("SELECT count(*) FROM portal_memberships")).scalar_one() == 0
        assert connection.execute(text("SELECT to_regclass('public.ledger_postings')")).scalar_one() is None
        assert connection.execute(text("SELECT to_regclass('public.resident_portal_sessions')")).scalar_one() is None
        assert connection.execute(text("SELECT to_regclass('public.maintenance_work_orders')")).scalar_one() is None
        assert connection.execute(text("SELECT to_regclass('public.message_threads')")).scalar_one() is None

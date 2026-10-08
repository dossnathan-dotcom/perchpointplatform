"""Phase 11 conflict-free showings, calendar mirrors, and fair-access boundaries."""
import hashlib
import hmac
import json
import os
import threading
from datetime import timezone
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.commands import CommandError
from perchpoint.db import runtime_transaction
from perchpoint.phase11_scheduling import resolve_wall
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
        assert client.post("/api/v2/portfolio/availability", headers=headers, json={"space_id": space.json()["id"], "availability": availability, "effective_on": day, "confidence": "exact", "source": "manager_confirmation", "reason": "Synthetic showing availability.", "idempotency_key": _key(name)}).status_code == 201
    assert client.post("/api/v2/portfolio/prices", headers=headers, json={"space_id": space.json()["id"], "amount_minor": 140000, "currency": "USD", "period": "monthly", "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": _key("price")}).status_code == 201
    assert client.post("/api/v2/portfolio/media", headers=headers, json={"space_id": space.json()["id"], "content": "JFIF-synthetic-front", "signature": "JFIF", "declared_mime": "image/jpeg", "alt_text": "Synthetic front of the home", "rights_state": "licensed", "idempotency_key": _key("media")}).status_code == 201
    slug = f"phase11-{uuid4().hex[:8]}"
    published = client.post("/api/v2/portfolio/snapshots", headers=headers, json={"listing_id": listing.json()["id"], "expected_version": 1, "public_slug": slug, "description": "EXAMPLE ONLY. Synthetic listing facts.", "idempotency_key": _key("publish")})
    assert client.post("/api/v2/discovery/project", headers=headers, json={"snapshot_id": published.json()["id"], "bedrooms": 2, "idempotency_key": _key("project")}).status_code == 201
    return slug


def _receipt(client, slug):
    response = client.post("/api/v2/public/leasing/inquiries", json={"name": "Casey Synthetic", "email": f"casey.{uuid4().hex[:8]}@example.com", "message": "Synthetic showing interest.", "disclosure": True, "public_slug": slug, "idempotency_key": _key("intake")})
    assert response.status_code == 201, response.text
    return response.json()["receipt"]


def _book(client, capability, wall="2026-10-20T10:00:00", key=None, **extra):
    body = {"capability": capability, "wall_start": wall, "zone_name": "America/New_York", "offset_minutes": -240, "mode": "individual", "guest_count": 1, "idempotency_key": key or _key("book")}
    body.update(extra)
    return client.post("/api/v2/public/showings", json=body)


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_wall_time_rejects_the_spring_gap_and_keeps_both_fall_offsets():
    with pytest.raises(CommandError) as gap:
        resolve_wall("2026-03-08T02:30:00", "America/New_York", -300)
    assert gap.value.code == "nonexistent_time"
    early = resolve_wall("2026-11-01T01:30:00", "America/New_York", -240)
    late = resolve_wall("2026-11-01T01:30:00", "America/New_York", -300)
    assert early.astimezone(timezone.utc) != late.astimezone(timezone.utc)
    assert early.astimezone(timezone.utc).isoformat() == "2026-11-01T05:30:00+00:00"


def test_showings_prevent_overlap_and_keep_provider_state_separate(client):
    session, headers = _login(client, "ann.synthetic@example.com")
    slug = _publish(client, headers, "Phase 11 Synthetic Court")
    receipt = _receipt(client, slug)
    capability = client.post("/api/v2/public/showings/capabilities", json={"receipt": receipt})
    assert capability.status_code == 200, capability.text
    token = capability.json()["capability"]
    slots = client.post("/api/v2/public/showings/slots", json={"capability": token, "day": "2026-10-20"})
    assert slots.status_code == 200 and slots.json()["slots"][0]["duration_minutes"] == 30
    assert "host" not in slots.text
    parent = client.post("/api/v2/leasing/showing-resources", headers=headers, json={"kind": "property", "label": f"Shared building {uuid4().hex[:8]}", "capacity": 1})
    left = client.post("/api/v2/leasing/showing-resources", headers=headers, json={"kind": "space", "label": "Left", "capacity": 4, "parent_id": parent.json()["id"]})
    right = client.post("/api/v2/leasing/showing-resources", headers=headers, json={"kind": "space", "label": "Right", "capacity": 4, "parent_id": parent.json()["id"]})
    host_a = client.post("/api/v2/leasing/showing-resources", headers=headers, json={"kind": "host", "label": "Host A"})
    host_b = client.post("/api/v2/leasing/showing-resources", headers=headers, json={"kind": "host", "label": "Host B"})
    resources = {"host_resource_id": host_a.json()["id"], "space_resource_id": left.json()["id"]}
    key = _key("same")
    booked = _book(client, token, key=key, **resources)
    assert booked.status_code == 200, booked.text
    assert booked.json()["duration_minutes"] == 30 and "buffer" not in booked.text
    replay = _book(client, token, key=key, **resources)
    assert replay.json()["replayed"] is True and replay.json()["reference"] == booked.json()["reference"]
    changed = _book(client, token, key=key, guest_count=2, **resources)
    assert changed.status_code == 409 and changed.json()["detail"]["code"] == "conflict"
    second = _book(client, token, **resources)
    assert second.status_code == 409 and second.json()["detail"]["code"] == "slot_unavailable"
    guided = _book(client, token, wall="2026-10-20T11:00:00", mode="self_guided", **resources)
    assert guided.status_code == 400
    sibling = _receipt(client, slug)
    sibling_token = client.post("/api/v2/public/showings/capabilities", json={"receipt": sibling}).json()["capability"]
    first_space = _book(client, sibling_token, wall="2026-10-21T10:00:00", host_resource_id=host_a.json()["id"], space_resource_id=left.json()["id"])
    assert first_space.status_code == 200, first_space.text
    other_space = _book(client, sibling_token, wall="2026-10-21T10:00:00", host_resource_id=host_b.json()["id"], space_resource_id=right.json()["id"])
    assert other_space.status_code == 409
    winners = []
    barrier = threading.Barrier(2)

    def race():
        barrier.wait()
        winners.append(_book(client, sibling_token, wall="2026-10-22T13:00:00", host_resource_id=host_a.json()["id"], space_resource_id=left.json()["id"]).status_code)

    threads = [threading.Thread(target=race) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(winners) == [200, 409]
    started = client.post("/api/v2/leasing/calendar/start", headers=headers)
    assert "fake-refresh-token" not in started.text
    finished = client.post("/api/v2/leasing/calendar/finish", headers=headers, json={"connection_id": started.json()["connection_id"], "code": "fake-auth-code", "state": started.json()["state"], "verifier": started.json()["verifier"], "challenge": started.json()["challenge"]})
    assert finished.status_code == 200 and "fake-refresh-token" not in finished.text
    forged = client.post("/api/v2/public/calendar/callbacks", content=b"{}", headers={"x-perchpoint-signature": "forged"})
    assert forged.status_code == 400
    body = json.dumps({"reference": booked.json()["reference"], "event_id": _key("event"), "change": "deleted"}).encode()
    signature = hmac.new(os.environ["PHASE2_WEBHOOK_SECRET"].encode(), body, hashlib.sha256).hexdigest()
    deleted = client.post("/api/v2/public/calendar/callbacks", content=body, headers={"x-perchpoint-signature": signature, "content-type": "application/json"})
    assert deleted.status_code == 200, deleted.text
    assert deleted.json()["business_state"] == "confirmed" and deleted.json()["sync_state"] == "drifted"
    replayed = client.post("/api/v2/public/calendar/callbacks", content=body, headers={"x-perchpoint-signature": signature, "content-type": "application/json"})
    assert replayed.json()["replayed"] is True
    completed = client.post("/api/v2/leasing/showings/complete", headers=headers, json={"reference": booked.json()["reference"]})
    assert completed.status_code == 200 and completed.json()["next_action"] == "showing_follow_up"
    _, isolation_headers = _login(client, "isolation.synthetic@example.com")
    hidden = client.post("/api/v2/leasing/showings/cancel", headers=isolation_headers, json={"reference": booked.json()["reference"]})
    assert hidden.status_code == 403
    with runtime_transaction(Settings.load(), None, None, uuid4()) as connection:
        assert connection.execute(text("SELECT count(*) FROM showings")).scalar_one() == 0
    assert session["organization_id"]

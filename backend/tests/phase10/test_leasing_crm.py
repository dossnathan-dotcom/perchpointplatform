"""Phase 10 inquiry capture, prospect identity, and leasing CRM boundaries."""
import os
import threading
from datetime import datetime
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from perchpoint.db import runtime_transaction
from perchpoint.routes import create_app
from perchpoint.settings import Settings


def _settings() -> Settings:
    return Settings.load()


def _login(client, email):
    response = client.post("/api/v2/session", json={"email": email, "password": os.environ["PHASE2_DEV_PASSWORD"]})
    assert response.status_code == 200, response.text
    return response.json(), {"Authorization": f"Bearer {response.json()['token']}"}


def _key(prefix):
    return f"{prefix}-{uuid4().hex}"


def _publish(client, headers, label):
    created = client.post(
        "/api/v2/properties",
        headers=headers,
        json={"name": label, "property_type": "mixed_use", "idempotency_key": _key("prop")},
    )
    assert created.status_code == 201, created.text
    building = client.post(
        "/api/v2/buildings",
        headers=headers,
        json={"property_id": created.json()["id"], "name": "Primary", "allowed_uses": ["residential"], "idempotency_key": _key("bldg")},
    )
    space = client.post(
        "/api/v2/spaces",
        headers=headers,
        json={"property_id": created.json()["id"], "building_id": building.json()["id"], "label": label, "use": "residential", "square_feet": 900, "idempotency_key": _key("space")},
    )
    assert space.status_code == 201, space.text
    listing = client.post(
        "/api/v2/listings",
        headers=headers,
        json={"space_id": space.json()["id"], "property_name": label, "label": label, "use": "residential", "municipality": "Cincinnati", "state": "OH", "amount_minor": 140000, "currency": "USD", "idempotency_key": _key("listing")},
    )
    assert listing.status_code == 201, listing.text
    for availability, day, name in (("coming_soon", "2026-10-01", "soon"), ("available", "2026-10-15", "open")):
        step = client.post(
            "/api/v2/portfolio/availability",
            headers=headers,
            json={"space_id": space.json()["id"], "availability": availability, "effective_on": day, "confidence": "exact", "source": "manager_confirmation", "reason": "Synthetic leasing availability.", "idempotency_key": _key(name)},
        )
        assert step.status_code == 201, step.text
    price = client.post(
        "/api/v2/portfolio/prices",
        headers=headers,
        json={"space_id": space.json()["id"], "amount_minor": 140000, "currency": "USD", "period": "monthly", "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": _key("price")},
    )
    assert price.status_code == 201, price.text
    media = client.post(
        "/api/v2/portfolio/media",
        headers=headers,
        json={"space_id": space.json()["id"], "content": "JFIF-synthetic-front", "signature": "JFIF", "declared_mime": "image/jpeg", "alt_text": "Synthetic front of the home", "rights_state": "licensed", "idempotency_key": _key("media")},
    )
    assert media.status_code == 201, media.text
    slug = f"phase10-{uuid4().hex[:8]}"
    published = client.post(
        "/api/v2/portfolio/snapshots",
        headers=headers,
        json={"listing_id": listing.json()["id"], "expected_version": 1, "public_slug": slug, "description": "EXAMPLE ONLY. Synthetic listing facts.", "idempotency_key": _key("publish")},
    )
    assert published.status_code == 201, published.text
    projected = client.post(
        "/api/v2/discovery/project",
        headers=headers,
        json={"snapshot_id": published.json()["id"], "bedrooms": 2, "idempotency_key": _key("project")},
    )
    assert projected.status_code == 201, projected.text
    return slug


def _public(client, **extra):
    body = {
        "name": extra.pop("name"),
        "email": extra.pop("email"),
        "message": extra.pop("message", "Synthetic interest in a HawkVision home."),
        "disclosure": True,
        "idempotency_key": extra.pop("idempotency_key", _key("intake")),
    }
    body.update(extra)
    return client.post("/api/v2/public/leasing/inquiries", json=body)


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_leasing_inquiry_keeps_prospect_clock_and_denies_cross_scope(client):
    session, headers = _login(client, "ann.synthetic@example.com")
    organization = session["organization_id"]
    slug = _publish(client, headers, "Phase 10 Synthetic Court")
    other = _publish(client, headers, "Phase 10 Synthetic Annex")
    email = f"casey.{uuid4().hex[:8]}@example.com"
    key = _key("same")
    created = _public(
        client,
        name="Casey Synthetic",
        email=email,
        public_slug=slug,
        search_ref="search-synthetic",
        position="2",
        first_touch="rentals",
        last_touch="listing",
        idempotency_key=key,
    )
    assert created.status_code == 201, created.text
    receipt = created.json()["receipt"]
    assert created.json()["replayed"] is False
    assert "prospect" not in created.json() and "inquiry" not in created.text
    replay = _public(client, name="Casey Synthetic", email=email, public_slug=slug, search_ref="search-synthetic", position="2", first_touch="rentals", last_touch="listing", idempotency_key=key)
    assert replay.status_code == 201 and replay.json()["receipt"] == receipt and replay.json()["replayed"] is True
    conflict = _public(client, name="Casey Synthetic", email=email, public_slug=other, idempotency_key=key)
    assert conflict.status_code == 409 and conflict.json()["detail"]["code"] == "conflict"
    assert _public(client, name="Casey Synthetic", email=email, public_slug=slug, honeypot="bot", idempotency_key=_key("bot")).status_code == 400
    assert _public(client, name="Casey Synthetic", email=email, public_slug=slug, organization_id=organization, idempotency_key=_key("forge")).status_code == 400
    assert _public(client, name="Casey Synthetic", email=email, public_slug=slug, lead_score="9", idempotency_key=_key("score")).status_code == 400
    assert _public(client, name="Casey Synthetic", email=email, public_slug=slug, attachment="id.pdf", idempotency_key=_key("file")).status_code == 400
    general = _public(client, name="General Synthetic", email=f"general.{uuid4().hex[:8]}@example.com")
    assert general.status_code == 201, general.text
    several = _public(client, name="Several Synthetic", email=f"several.{uuid4().hex[:8]}@example.com", slugs=f"{slug},{other}")
    assert several.status_code == 201, several.text
    linked = _public(client, name="Casey Synthetic", email=email, public_slug=other)
    assert linked.status_code == 201, linked.text
    named = _public(client, name="Casey Synthetic", email=f"other.{uuid4().hex[:8]}@example.com", public_slug=slug)
    assert named.status_code == 201, named.text
    gpc = client.post(
        "/api/v2/public/leasing/inquiries",
        headers={"sec-gpc": "1"},
        json={"name": "Quiet Synthetic", "email": f"quiet.{uuid4().hex[:8]}@example.com", "message": "Synthetic interest.", "disclosure": True, "marketing_opt_in": True, "idempotency_key": _key("gpc")},
    )
    assert gpc.status_code == 201, gpc.text
    failed = _public(client, name="Retry Synthetic", email=f"retry.{uuid4().hex[:8]}@example.com", public_slug=slug, fail_delivery=True)
    assert failed.status_code == 201 and failed.json()["status"] == "received"

    first = client.get(f"/api/v2/leasing/inquiries/{receipt}", headers=headers)
    assert first.status_code == 200, first.text
    assert first.json()["source"] == "website"
    assert first.json()["qualified"] is False
    assert first.json()["next_action"] == "review_inquiry"
    assert first.json()["interests"][0]["has_snapshot"] is True
    assert first.json()["attribution"]["direct_source"] == "website"
    assert first.json()["attribution"]["first_touch"] == "rentals"
    second = client.get(f"/api/v2/leasing/inquiries/{linked.json()['receipt']}", headers=headers)
    assert second.json()["prospect_id"] == first.json()["prospect_id"]
    ambiguous = client.get(f"/api/v2/leasing/inquiries/{named.json()['receipt']}", headers=headers)
    assert ambiguous.json()["prospect_id"] != first.json()["prospect_id"]
    assert "same_name" in ambiguous.json()["candidate_reasons"]
    general_detail = client.get(f"/api/v2/leasing/inquiries/{general.json()['receipt']}", headers=headers)
    assert general_detail.json()["general_interest"] is True and general_detail.json()["interests"] == []
    multi = client.get(f"/api/v2/leasing/inquiries/{several.json()['receipt']}", headers=headers)
    assert {item["public_slug"] for item in multi.json()["interests"]} == {slug, other}
    gpc_detail = client.get(f"/api/v2/leasing/inquiries/{gpc.json()['receipt']}", headers=headers)
    assert "marketing" not in {item["purpose"] for item in gpc_detail.json()["consents"]}
    assert gpc_detail.json()["attribution"]["gpc"] is True

    staff = client.post(
        "/api/v2/leasing/inquiries",
        headers=headers,
        json={"name": "Phone Synthetic", "email": f"phone.{uuid4().hex[:8]}@example.com", "source": "phone", "received_at": "2026-10-09T14:00:00+00:00", "idempotency_key": _key("phone")},
    )
    assert staff.status_code == 201, staff.text
    assert datetime.fromisoformat(staff.json()["deadline"]) == datetime.fromisoformat("2026-10-09T16:00:00+00:00")
    engine = create_engine(os.environ["PHASE2_ADMIN_URL"].rsplit("/", 1)[0] + "/perchpoint_phase2")
    with engine.begin() as connection:
        connection.execute(text("DELETE FROM business_closures WHERE organization_id = :org"), {"org": organization})
    weekend = client.post(
        "/api/v2/leasing/inquiries",
        headers=headers,
        json={"name": "Weekend Synthetic", "email": f"weekend.{uuid4().hex[:8]}@example.com", "source": "walk_in", "received_at": "2026-10-10T15:00:00+00:00", "idempotency_key": _key("weekend")},
    )
    assert datetime.fromisoformat(weekend.json()["deadline"]) == datetime.fromisoformat("2026-10-12T15:00:00+00:00")
    early = client.post(
        "/api/v2/leasing/inquiries",
        headers=headers,
        json={"name": "Early Synthetic", "email": f"early.{uuid4().hex[:8]}@example.com", "source": "forwarded", "received_at": "2026-10-09T12:00:00+00:00", "idempotency_key": _key("early")},
    )
    assert datetime.fromisoformat(early.json()["deadline"]) == datetime.fromisoformat("2026-10-09T15:00:00+00:00")
    dst = client.post(
        "/api/v2/leasing/inquiries",
        headers=headers,
        json={"name": "DST Synthetic", "email": f"dst.{uuid4().hex[:8]}@example.com", "source": "phone", "received_at": "2026-10-30T20:00:00+00:00", "idempotency_key": _key("dst")},
    )
    assert datetime.fromisoformat(dst.json()["deadline"]) == datetime.fromisoformat("2026-11-02T16:00:00+00:00")
    website = client.post(
        "/api/v2/leasing/inquiries",
        headers=headers,
        json={"name": "Relabel Synthetic", "email": f"relabel.{uuid4().hex[:8]}@example.com", "source": "website", "received_at": "2026-10-09T14:00:00+00:00", "idempotency_key": _key("website")},
    )
    assert website.status_code == 422

    with engine.begin() as connection:
        connection.execute(
            text("INSERT INTO business_closures (organization_id, closed_on, reason) VALUES (:org, '2026-10-12', 'synthetic holiday') ON CONFLICT DO NOTHING"),
            {"org": organization},
        )
    holiday = client.post(
        "/api/v2/leasing/inquiries",
        headers=headers,
        json={"name": "Holiday Synthetic", "email": f"holiday.{uuid4().hex[:8]}@example.com", "source": "phone", "received_at": "2026-10-12T14:00:00+00:00", "idempotency_key": _key("holiday")},
    )
    assert datetime.fromisoformat(holiday.json()["deadline"]) == datetime.fromisoformat("2026-10-13T15:00:00+00:00")

    note = client.post(
        "/api/v2/leasing/notes",
        headers=headers,
        json={"receipt": receipt, "body": "<script>alert(1)</script> Called back.", "idempotency_key": _key("note")},
    )
    assert note.status_code == 201
    with engine.begin() as connection:
        stored = connection.execute(text("SELECT body FROM leasing_notes WHERE id = :id"), {"id": note.json()["id"]}).scalar()
    assert "<" not in stored
    engine.dispose()
    denied_tag = client.post("/api/v2/leasing/tags", headers=headers, json={"code": "race", "idempotency_key": _key("tag")})
    assert denied_tag.status_code == 422
    allowed_tag = client.post("/api/v2/leasing/tags", headers=headers, json={"code": f"callback_{uuid4().hex[:8]}", "idempotency_key": _key("tag-ok")})
    assert allowed_tag.status_code == 201

    metrics_before = client.get("/api/v2/leasing/metrics", headers=headers)
    assert metrics_before.json()["showing_conversion"] is None
    assert metrics_before.json()["receipts_are_not_responses"] is True
    before_human = metrics_before.json()["human_responses"]
    attempt = client.post(
        "/api/v2/leasing/attempts",
        headers=headers,
        json={"receipt": receipt, "outcome": "spoke", "summary": "Confirmed interest.", "idempotency_key": _key("attempt")},
    )
    assert attempt.status_code == 201 and attempt.json()["qualified"] is True
    after = client.get(f"/api/v2/leasing/inquiries/{receipt}", headers=headers)
    assert after.json()["qualified"] is True
    assert client.get("/api/v2/leasing/metrics", headers=headers).json()["human_responses"] == before_human + 1
    suppressed = client.post("/api/v2/leasing/suppressions", headers=headers, json={"email": email, "idempotency_key": _key("suppress")})
    assert suppressed.status_code == 200
    blocked = client.post(
        "/api/v2/leasing/attempts",
        headers=headers,
        json={"receipt": linked.json()["receipt"], "outcome": "spoke", "summary": "Should not send.", "idempotency_key": _key("blocked")},
    )
    assert blocked.status_code == 403 and blocked.json()["detail"]["code"] == "suppressed"

    dry = client.post(
        "/api/v2/leasing/merges",
        headers=headers,
        json={"survivor_id": first.json()["prospect_id"], "alias_id": ambiguous.json()["prospect_id"], "expected_version": 1, "reason": "Same person confirmed by staff.", "dry_run": True, "idempotency_key": _key("dry")},
    )
    assert dry.status_code == 200 and dry.json()["dry_run"] is True and dry.json()["inquiries"] >= 1
    merged = client.post(
        "/api/v2/leasing/merges",
        headers=headers,
        json={"survivor_id": first.json()["prospect_id"], "alias_id": ambiguous.json()["prospect_id"], "expected_version": 1, "reason": "Same person confirmed by staff.", "idempotency_key": _key("merge")},
    )
    assert merged.status_code == 200, merged.text
    assert client.get(f"/api/v2/leasing/inquiries/{named.json()['receipt']}", headers=headers).json()["prospect_id"] == first.json()["prospect_id"]
    stale = client.post(
        "/api/v2/leasing/merges",
        headers=headers,
        json={"survivor_id": first.json()["prospect_id"], "alias_id": ambiguous.json()["prospect_id"], "expected_version": 1, "reason": "Repeated.", "idempotency_key": _key("stale-merge")},
    )
    assert stale.status_code == 404
    restored = client.post(
        "/api/v2/leasing/unmerges",
        headers=headers,
        json={"alias_id": ambiguous.json()["prospect_id"], "idempotency_key": _key("unmerge")},
    )
    assert restored.status_code == 200, restored.text
    assert client.get(f"/api/v2/leasing/inquiries/{named.json()['receipt']}", headers=headers).json()["prospect_id"] == ambiguous.json()["prospect_id"]

    statuses = []

    def claim_once():
        response = client.post(
            "/api/v2/leasing/claims",
            headers=headers,
            json={"receipt": general.json()["receipt"], "expected_version": 1, "idempotency_key": _key("claim")},
        )
        statuses.append(response.status_code)

    threads = [threading.Thread(target=claim_once) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    assert sorted(statuses) == [200, 409]

    closed = client.post(
        "/api/v2/leasing/transitions",
        headers=headers,
        json={"receipt": receipt, "expected_version": first.json()["version"], "stage": "closed", "idempotency_key": _key("close-missing")},
    )
    assert closed.status_code == 422
    current = client.get(f"/api/v2/leasing/inquiries/{receipt}", headers=headers).json()["version"]
    closed = client.post(
        "/api/v2/leasing/transitions",
        headers=headers,
        json={"receipt": receipt, "expected_version": current, "stage": "closed", "reason": "no_response", "idempotency_key": _key("close")},
    )
    assert closed.status_code == 200, closed.text
    reopened = client.post(
        "/api/v2/leasing/transitions",
        headers=headers,
        json={"receipt": receipt, "expected_version": closed.json()["version"], "stage": "new", "reason": "prospect_replied", "idempotency_key": _key("reopen")},
    )
    assert reopened.status_code == 200 and reopened.json()["stage"] == "new"
    assert client.get(f"/api/v2/leasing/inquiries/{receipt}", headers=headers).json()["next_action"] == "review_reopened"

    withdrawn = client.post("/api/v2/discovery/withdraw", headers=headers, json={"public_slug": slug, "idempotency_key": _key("withdraw")})
    assert withdrawn.status_code == 200, withdrawn.text
    historical = _public(client, name="Historical Synthetic", email=f"historical.{uuid4().hex[:8]}@example.com", public_slug=slug)
    assert historical.status_code == 201 and "withdrawn" not in historical.text
    historical_detail = client.get(f"/api/v2/leasing/inquiries/{historical.json()['receipt']}", headers=headers)
    assert historical_detail.json()["interests"][0]["availability_state"] == "historical"

    queue = client.get("/api/v2/leasing/queue", headers=headers, params={"receipt": receipt})
    assert queue.status_code == 200 and any(row["public_receipt"] == receipt for row in queue.json()["inquiries"])
    owner = client.get("/api/v2/leasing/owner-summary", headers=headers)
    assert owner.status_code == 403
    _faruk, faruk_headers = _login(client, "faruk.synthetic@example.com")
    summary = client.get("/api/v2/leasing/owner-summary", headers=faruk_headers)
    assert summary.status_code == 200 and summary.json()["names_included"] is False and "email" not in summary.text
    _isolation, isolation_headers = _login(client, "isolation.synthetic@example.com")
    hidden = client.get(f"/api/v2/leasing/inquiries/{receipt}", headers=isolation_headers)
    assert hidden.status_code == 403
    foreign = client.get("/api/v2/leasing/queue", headers=isolation_headers)
    assert foreign.status_code == 403
    with runtime_transaction(_settings(), None, None, uuid4()) as connection:
        visible = connection.execute(text("SELECT count(*) FROM leasing_inquiries")).scalar()
    assert visible == 0

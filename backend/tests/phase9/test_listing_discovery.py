"""Phase 9 discovery, owned distribution, and privacy boundaries."""
import json
import os
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
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _key(prefix):
    return f"{prefix}-{uuid4().hex}"


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_discovery_projects_search_withdraws_and_denies(client):
    headers = _login(client, "ann.synthetic@example.com")
    created = client.post(
        "/api/v2/properties",
        headers=headers,
        json={"name": "Phase 9 Synthetic Court", "property_type": "mixed_use", "idempotency_key": _key("prop")},
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
        json={"property_id": created.json()["id"], "building_id": building.json()["id"], "label": "Home 9", "use": "residential", "square_feet": 900, "idempotency_key": _key("space")},
    )
    assert space.status_code == 201, space.text
    space_id = space.json()["id"]
    listing = client.post(
        "/api/v2/listings",
        headers=headers,
        json={"space_id": space_id, "property_name": "Phase 9 Synthetic Court", "label": "Home 9", "use": "residential", "municipality": "Cincinnati", "state": "OH", "amount_minor": 140000, "currency": "USD", "idempotency_key": _key("listing")},
    )
    assert listing.status_code == 201, listing.text
    listing_id = listing.json()["id"]
    for availability, day, name in (("coming_soon", "2026-10-01", "soon"), ("available", "2026-10-15", "open")):
        step = client.post(
            "/api/v2/portfolio/availability",
            headers=headers,
            json={"space_id": space_id, "availability": availability, "effective_on": day, "confidence": "exact", "source": "manager_confirmation", "reason": "Synthetic discovery availability.", "idempotency_key": _key(name)},
        )
        assert step.status_code == 201, step.text
    price = client.post(
        "/api/v2/portfolio/prices",
        headers=headers,
        json={"space_id": space_id, "amount_minor": 140000, "currency": "USD", "period": "monthly", "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": _key("price")},
    )
    assert price.status_code == 201, price.text
    media = client.post(
        "/api/v2/portfolio/media",
        headers=headers,
        json={"space_id": space_id, "content": "JFIF-synthetic-front", "signature": "JFIF", "declared_mime": "image/jpeg", "alt_text": "Synthetic front of the home", "rights_state": "licensed", "idempotency_key": _key("media")},
    )
    assert media.status_code == 201, media.text
    slug = f"phase9-{uuid4().hex[:8]}"
    published = client.post(
        "/api/v2/portfolio/snapshots",
        headers=headers,
        json={"listing_id": listing_id, "expected_version": 1, "public_slug": slug, "description": "EXAMPLE ONLY. Synthetic listing facts.", "idempotency_key": _key("publish")},
    )
    assert published.status_code == 201, published.text
    projected = client.post(
        "/api/v2/discovery/project",
        headers=headers,
        json={"snapshot_id": published.json()["id"], "bedrooms": 2, "idempotency_key": _key("project")},
    )
    assert projected.status_code == 201, projected.text
    claimed = []
    for index in range(5):
        job = client.post("/api/v2/discovery/jobs/claim", headers=headers, json={"projection_id": projected.json()["id"], "idempotency_key": _key(f"claim-{index}")})
        assert job.status_code == 200 and job.json()["claimed"] is True, job.text
        claimed.append(job.json())
    assert len({item["id"] for item in claimed}) == 5
    engine = create_engine(os.environ["PHASE2_ADMIN_URL"].rsplit("/", 1)[0] + "/perchpoint_phase2")
    with engine.begin() as connection:
        connection.execute(text("UPDATE distribution_operations SET lease_expires = now() - interval '1 minute' WHERE id = :id"), {"id": claimed[0]["id"]})
    engine.dispose()
    reclaimed = client.post("/api/v2/discovery/jobs/claim", headers=headers, json={"projection_id": projected.json()["id"], "idempotency_key": _key("reclaim")})
    assert reclaimed.status_code == 200 and reclaimed.json()["id"] == claimed[0]["id"] and reclaimed.json()["attempts"] >= 2
    stale = client.post(
        "/api/v2/discovery/jobs/complete",
        headers=headers,
        json={"operation_id": claimed[1]["id"], "expected_version": 0, "idempotency_key": _key("stale")},
    )
    assert stale.status_code == 200 and stale.json()["state"] == "stale"
    dead = client.post(
        "/api/v2/discovery/jobs/complete",
        headers=headers,
        json={"operation_id": claimed[2]["id"], "expected_version": claimed[2]["projection_version"], "terminal": True, "idempotency_key": _key("dead")},
    )
    assert dead.status_code == 200 and dead.json()["state"] == "dead_letter"
    rejected_pets = client.post(
        "/api/v2/discovery/project",
        headers=headers,
        json={"snapshot_id": published.json()["id"], "pet_policy": "assistance_animal", "idempotency_key": _key("pets")},
    )
    assert rejected_pets.status_code == 422
    found = client.get("/api/v2/public/discovery/search", params={"city": "Cincinnati", "use_code": "residential", "min_bedrooms": 2, "query": "Synthetic"})
    assert found.status_code == 200, found.text
    assert any(row["public_slug"] == slug for row in found.json()["records"])
    assert found.json()["facets"]["residential"] >= 1
    assert found.json()["canonical_query"] == "&".join(sorted(found.json()["canonical_query"].split("&")))
    commercial = client.get("/api/v2/public/discovery/search", params={"use_code": "commercial", "city": "Cincinnati"})
    assert all(row["public_slug"] != slug for row in commercial.json()["records"])
    space_two = client.post(
        "/api/v2/spaces",
        headers=headers,
        json={"property_id": created.json()["id"], "building_id": building.json()["id"], "label": "Home 9B", "use": "residential", "square_feet": 1100, "idempotency_key": _key("space-b")},
    )
    assert space_two.status_code == 201, space_two.text
    listing_two = client.post(
        "/api/v2/listings",
        headers=headers,
        json={"space_id": space_two.json()["id"], "property_name": "Phase 9 Synthetic Court", "label": "Home 9B", "use": "residential", "municipality": "Cincinnati", "state": "OH", "amount_minor": 160000, "currency": "USD", "idempotency_key": _key("listing-b")},
    )
    assert listing_two.status_code == 201, listing_two.text
    for availability, day, name in (("coming_soon", "2026-10-01", "soon-b"), ("available", "2026-10-20", "open-b")):
        step = client.post(
            "/api/v2/portfolio/availability",
            headers=headers,
            json={"space_id": space_two.json()["id"], "availability": availability, "effective_on": day, "confidence": "exact", "source": "manager_confirmation", "reason": "Synthetic discovery availability.", "idempotency_key": _key(name)},
        )
        assert step.status_code == 201, step.text
    priced = client.post(
        "/api/v2/portfolio/prices",
        headers=headers,
        json={"space_id": space_two.json()["id"], "amount_minor": 160000, "currency": "USD", "period": "monthly", "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": _key("price-b")},
    )
    assert priced.status_code == 201, priced.text
    media_two = client.post(
        "/api/v2/portfolio/media",
        headers=headers,
        json={"space_id": space_two.json()["id"], "content": "JFIF-synthetic-side", "signature": "JFIF", "declared_mime": "image/jpeg", "alt_text": "Synthetic side of the home", "rights_state": "licensed", "idempotency_key": _key("media-b")},
    )
    assert media_two.status_code == 201, media_two.text
    slug_two = f"phase9b-{uuid4().hex[:8]}"
    postal = f"9{uuid4().hex[:5]}"
    neighborhood = f"clifton-{uuid4().hex[:6]}"
    published_two = client.post(
        "/api/v2/portfolio/snapshots",
        headers=headers,
        json={"listing_id": listing_two.json()["id"], "expected_version": 1, "public_slug": slug_two, "description": "EXAMPLE ONLY. Synthetic listing facts.", "idempotency_key": _key("publish-b")},
    )
    assert published_two.status_code == 201, published_two.text
    projected_two = client.post(
        "/api/v2/discovery/project",
        headers=headers,
        json={
            "snapshot_id": published_two.json()["id"],
            "neighborhood": neighborhood,
            "postal_code": postal,
            "pet_policy": "cats",
            "amenities": ["parking"],
            "accessibility_features": ["step_free"],
            "verification_on": "2026-10-01",
            "latitude": 39.132,
            "longitude": -84.512,
            "available_on": "2026-10-20",
            "idempotency_key": _key("project-b"),
        },
    )
    assert projected_two.status_code == 201, projected_two.text
    unknown_beds = client.get("/api/v2/public/discovery/search", params={"postal_code": postal, "min_bedrooms": 1})
    assert all(row["public_slug"] != slug_two for row in unknown_beds.json()["records"])
    located = client.get("/api/v2/public/discovery/search", params={"neighborhood": neighborhood, "postal_code": postal, "pet_policy": "cats", "amenity": "parking", "accessibility": "step_free"})
    assert any(row["public_slug"] == slug_two for row in located.json()["records"])
    located_body = json.dumps(located.json())
    assert "not a compliance or suitability determination" in located_body
    assert "ADA" not in located_body
    early = client.get("/api/v2/public/discovery/search", params={"postal_code": postal, "move_in": "2026-10-01"})
    assert all(row["public_slug"] != slug_two for row in early.json()["records"])
    later = client.get("/api/v2/public/discovery/search", params={"postal_code": postal, "move_in": "2026-11-01"})
    assert any(row["public_slug"] == slug_two for row in later.json()["records"])
    nearby = client.get("/api/v2/public/discovery/search", params={"postal_code": postal, "origin_lat": "39.132", "origin_lon": "-84.512", "radius_km": "2"})
    assert any(row["public_slug"] == slug_two for row in nearby.json()["records"])
    distant = client.get("/api/v2/public/discovery/search", params={"origin_lat": "41.000", "origin_lon": "-84.512", "radius_km": "2"})
    assert all(row["public_slug"] != slug_two for row in distant.json()["records"])
    page_one = client.get("/api/v2/public/discovery/search", params={"city": "Cincinnati", "use_code": "residential", "limit": 1, "offset": 0, "sort": "price_asc"})
    page_two = client.get("/api/v2/public/discovery/search", params={"city": "Cincinnati", "use_code": "residential", "limit": 1, "offset": 1, "sort": "price_asc"})
    assert page_one.json()["total"] == page_two.json()["total"] and page_one.json()["total"] >= 2
    assert page_one.json()["records"][0]["public_slug"] != page_two.json()["records"][0]["public_slug"]
    empty = client.get("/api/v2/public/discovery/search", params={"postal_code": "00000", "min_bedrooms": 9, "max_amount": 1})
    assert empty.json()["total"] == 0 and "does not broaden" in empty.json()["zero_result"]["relaxation"]
    compared = client.get("/api/v2/public/discovery/compare", params={"slugs": f"{slug},{slug_two},missing,extra"})
    assert [row.get("use_code") for row in compared.json()["records"]] == ["residential", "residential"]
    assert len(compared.json()["records"]) == 2
    marketed = client.get("/api/v2/discovery/marketed", headers=headers, params={"public_slug": slug})
    assert marketed.status_code == 200 and marketed.json()["episode_days"] >= 0 and marketed.json()["timezone"] == "America/New_York"
    expensive = client.get("/api/v2/public/discovery/search", params={"city": "Cincinnati", "max_amount": 1000})
    assert all(row["public_slug"] != slug for row in expensive.json()["records"])
    detail = client.get(f"/api/v2/public/discovery/listings/{slug}")
    assert detail.status_code == 200
    assert "organization_id" not in detail.json()
    sitemap = client.get("/api/v2/public/discovery/sitemap.xml")
    assert slug in sitemap.json()["xml"]
    event_key = _key("event")
    event = client.post(
        "/api/v2/public/discovery/events",
        json={"event_name": "detail", "listing_slug": slug, "session_ref": "synthetic-session", "source": "direct", "medium": "none", "campaign": "example", "idempotency_key": event_key},
    )
    assert event.status_code == 201 and event.json()["counted"] is True
    repeated = client.post(
        "/api/v2/public/discovery/events",
        json={"event_name": "detail", "listing_slug": slug, "session_ref": "synthetic-session", "source": "direct", "medium": "none", "campaign": "example", "idempotency_key": event_key},
    )
    assert repeated.status_code == 201 and repeated.json()["replayed"] is True
    # The response does not echo the key. Send the original body key by reconstructing is not available.
    # A second call with a fresh key and GPC must not count.
    suppressed = client.post(
        "/api/v2/public/discovery/events",
        headers={"sec-gpc": "1"},
        json={"event_name": "cta", "listing_slug": slug, "session_ref": "synthetic-session", "idempotency_key": _key("gpc")},
    )
    assert suppressed.status_code == 201 and suppressed.json()["counted"] is False
    bot = client.post(
        "/api/v2/public/discovery/events",
        json={"event_name": "impression", "listing_slug": slug, "session_ref": "synthetic-session", "classification": "bot", "idempotency_key": _key("bot")},
    )
    assert bot.status_code == 201 and bot.json()["counted"] is False and bot.json()["classification"] == "bot"
    handoff = client.post(
        "/api/v2/public/discovery/events",
        json={"event_name": "cta", "listing_slug": slug, "session_ref": "synthetic-session", "source": "direct", "medium": "none", "campaign": "example", "idempotency_key": _key("cta")},
    )
    assert handoff.status_code == 201 and handoff.json()["counted"] is True and len(handoff.json()["handoff_ref"]) == 64
    leaked = client.post(
        "/api/v2/public/discovery/events",
        json={"event_name": "detail", "listing_slug": slug, "session_ref": "a@example.com", "idempotency_key": _key("pii")},
    )
    assert leaked.status_code == 422
    denied = client.post(
        "/api/v2/discovery/ranking",
        headers=headers,
        json={"version": 1, "reason": "Synthetic ranking review.", "effective_on": "2026-10-01", "idempotency_key": _key("rank")},
    )
    assert denied.status_code == 403
    owner = _login(client, "faruk.synthetic@example.com")
    approved = client.post(
        "/api/v2/discovery/ranking",
        headers=owner,
        json={"version": 1, "reason": "Synthetic ranking review.", "effective_on": "2026-10-01", "idempotency_key": _key("rank-owner")},
    )
    assert approved.status_code == 201, approved.text
    blocked = client.post(
        "/api/v2/discovery/project",
        headers=headers,
        json={"snapshot_id": published.json()["id"], "target": "zillow", "idempotency_key": _key("zillow")},
    )
    assert blocked.status_code == 422
    removed = client.post(
        "/api/v2/discovery/withdraw",
        headers=headers,
        json={"public_slug": slug, "idempotency_key": _key("withdraw")},
    )
    assert removed.status_code == 200, removed.text
    hidden = client.get("/api/v2/public/discovery/search", params={"city": "Cincinnati", "query": slug})
    assert all(row["public_slug"] != slug for row in hidden.json()["records"])
    gone = client.get(f"/api/v2/public/discovery/listings/{slug}")
    assert gone.status_code == 410
    paused = client.get("/api/v2/discovery/marketed", headers=headers, params={"public_slug": slug})
    assert paused.status_code == 200 and paused.json()["episode_days"] == 0 and paused.json()["eligibility"] == "withdrawn"
    after = client.get("/api/v2/public/discovery/sitemap.xml")
    assert f"/rentals/{slug}" not in after.json()["xml"]
    report = client.post("/api/v2/discovery/reconcile", headers=headers, json={"idempotency_key": _key("reconcile")})
    assert report.status_code == 200 and report.json()["status"] == "completed"
    health = client.get("/api/v2/discovery/health", headers=headers)
    assert health.status_code == 200 and health.json()["external_syndication"] == "disabled"
    with runtime_transaction(_settings(), None, None, uuid4()) as connection:
        visible = connection.execute(text("SELECT count(*) FROM discovery_projections")).scalar()
    assert visible == 0

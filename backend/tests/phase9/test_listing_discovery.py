"""Phase 9 discovery, owned distribution, and privacy boundaries."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

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
    found = client.get("/api/v2/public/discovery/search", params={"city": "Cincinnati", "use_code": "residential", "min_bedrooms": 2, "query": "Synthetic"})
    assert found.status_code == 200, found.text
    assert any(row["public_slug"] == slug for row in found.json()["records"])
    assert found.json()["facets"]["residential"] >= 1
    commercial = client.get("/api/v2/public/discovery/search", params={"use_code": "commercial", "city": "Cincinnati"})
    assert all(row["public_slug"] != slug for row in commercial.json()["records"])
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
    after = client.get("/api/v2/public/discovery/sitemap.xml")
    assert f"/rentals/{slug}" not in after.json()["xml"]
    report = client.post("/api/v2/discovery/reconcile", headers=headers, json={"idempotency_key": _key("reconcile")})
    assert report.status_code == 200 and report.json()["status"] == "completed"
    health = client.get("/api/v2/discovery/health", headers=headers)
    assert health.status_code == 200 and health.json()["external_syndication"] == "disabled"
    with runtime_transaction(_settings(), None, None, uuid4()) as connection:
        visible = connection.execute(text("SELECT count(*) FROM discovery_projections")).scalar()
    assert visible == 0

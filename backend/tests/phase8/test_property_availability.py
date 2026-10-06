"""Phase 8 pricing, readiness, media review, and publication snapshots."""
import os
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from perchpoint.db import engine_for, runtime_transaction
from perchpoint.routes import create_app
from perchpoint.settings import Settings


def _settings() -> Settings:
    return Settings.load()


def _login(client, email):
    response = client.post("/api/v2/session", json={"email": email, "password": os.environ["PHASE2_DEV_PASSWORD"]})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def _key(prefix):
    return f"{prefix}-{uuid4().hex}"


def _workspace(client, token):
    headers = _auth(token)
    created = client.post(
        "/api/v2/properties",
        headers=headers,
        json={"name": "Phase 8 Synthetic Court", "property_type": "mixed_use", "idempotency_key": _key("prop")},
    )
    assert created.status_code == 201, created.text
    property_id = created.json()["id"]
    building = client.post(
        "/api/v2/buildings",
        headers=headers,
        json={"property_id": property_id, "name": "Primary", "allowed_uses": ["residential", "commercial"], "idempotency_key": _key("bldg")},
    )
    assert building.status_code == 201, building.text
    space = client.post(
        "/api/v2/spaces",
        headers=headers,
        json={
            "property_id": property_id,
            "building_id": building.json()["id"],
            "label": "Home 1",
            "use": "residential",
            "square_feet": 980,
            "idempotency_key": _key("space"),
        },
    )
    assert space.status_code == 201, space.text
    listing = client.post(
        "/api/v2/listings",
        headers=headers,
        json={
            "space_id": space.json()["id"],
            "property_name": "Phase 8 Synthetic Court",
            "label": "Home 1",
            "use": "residential",
            "municipality": "Cincinnati",
            "state": "OH",
            "amount_minor": 150000,
            "currency": "USD",
            "idempotency_key": _key("listing"),
        },
    )
    assert listing.status_code == 201, listing.text
    return headers, property_id, space.json()["id"], listing.json()["id"]


def test_portfolio_truth_publication_and_denial(client):
    ann = _login(client, "ann.synthetic@example.com")
    headers, property_id, space_id, listing_id = _workspace(client, ann)
    inventory = client.get("/api/v2/portfolio/inventory", headers=headers, params={"limit": 100})
    assert inventory.status_code == 200
    assert any(row["space_id"] == space_id for row in inventory.json()["records"])
    readiness = client.post(
        "/api/v2/portfolio/readiness",
        headers=headers,
        json={"space_id": space_id, "readiness": "turn_required", "reason": "Synthetic turn is required.", "idempotency_key": _key("ready")},
    )
    assert readiness.status_code == 201, readiness.text
    blocked = client.post(
        "/api/v2/portfolio/readiness",
        headers=headers,
        json={"space_id": space_id, "readiness": "ready", "reason": "Skipping the required work.", "idempotency_key": _key("ready-bad")},
    )
    assert blocked.status_code == 422
    available = client.post(
        "/api/v2/portfolio/availability",
        headers=headers,
        json={
            "space_id": space_id,
            "availability": "coming_soon",
            "effective_on": "2026-10-01",
            "confidence": "estimated",
            "source": "manager_confirmation",
            "reason": "Synthetic coming soon window.",
            "idempotency_key": _key("avail"),
        },
    )
    assert available.status_code == 201, available.text
    offered = client.post(
        "/api/v2/portfolio/availability",
        headers=headers,
        json={
            "space_id": space_id,
            "availability": "available",
            "effective_on": "2026-10-15",
            "confidence": "exact",
            "source": "manager_confirmation",
            "reason": "Synthetic availability is confirmed.",
            "idempotency_key": _key("avail-open"),
        },
    )
    assert offered.status_code == 201, offered.text
    price_key = _key("price")
    price = client.post(
        "/api/v2/portfolio/prices",
        headers=headers,
        json={"space_id": space_id, "amount_minor": 150000, "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": price_key},
    )
    assert price.status_code == 201 and price.json()["applied"] is True
    replay = client.post(
        "/api/v2/portfolio/prices",
        headers=headers,
        json={"space_id": space_id, "amount_minor": 150000, "effective_on": "2026-10-01", "reason": "Synthetic asking rent.", "idempotency_key": price_key},
    )
    assert replay.status_code == 201 and replay.json()["id"] == price.json()["id"]
    conflict = client.post(
        "/api/v2/portfolio/prices",
        headers=headers,
        json={"space_id": space_id, "amount_minor": 151000, "effective_on": "2026-11-01", "reason": "Different payload.", "idempotency_key": price_key},
    )
    assert conflict.status_code == 409
    material = client.post(
        "/api/v2/portfolio/prices",
        headers=headers,
        json={"space_id": space_id, "amount_minor": 200000, "effective_on": "2026-11-01", "reason": "Material synthetic increase.", "idempotency_key": _key("material")},
    )
    assert material.status_code == 201 and material.json()["applied"] is False and material.json()["status"] == "prepared"
    faruk = _auth(_login(client, "faruk.synthetic@example.com"))
    approved = client.post(
        "/api/v2/portfolio/prices",
        headers=faruk,
        json={"space_id": space_id, "amount_minor": 200000, "effective_on": "2026-11-01", "reason": "Owner approved synthetic increase.", "idempotency_key": _key("owner-price")},
    )
    assert approved.status_code == 201 and approved.json()["applied"] is True and approved.json()["approval_state"] == "owner_approved"
    fee = client.post(
        "/api/v2/portfolio/fees",
        headers=headers,
        json={
            "space_id": space_id,
            "code": "application",
            "label": "Synthetic application fee",
            "amount_minor": 4500,
            "required": True,
            "recurring": False,
            "refundable": False,
            "effective_on": "2026-10-01",
            "idempotency_key": _key("fee"),
        },
    )
    assert fee.status_code == 201, fee.text
    utility = client.post(
        "/api/v2/portfolio/utilities",
        headers=headers,
        json={
            "space_id": space_id,
            "utility_code": "electric",
            "responsibility": "tenant_paid",
            "explanation": "EXAMPLE ONLY. Separately metered electric.",
            "effective_on": "2026-10-01",
            "idempotency_key": _key("utility"),
        },
    )
    assert utility.status_code == 201, utility.text
    concession = client.post(
        "/api/v2/portfolio/concessions",
        headers=headers,
        json={
            "space_id": space_id,
            "label": "Synthetic first month",
            "amount_minor": 5000,
            "effective_on": "2026-10-01",
            "ended_on": "2026-11-01",
            "idempotency_key": _key("concession"),
        },
    )
    assert concession.status_code == 201, concession.text
    media = client.post(
        "/api/v2/portfolio/media",
        headers=headers,
        json={
            "space_id": space_id,
            "content": "JFIF-synthetic-front",
            "signature": "JFIF",
            "declared_mime": "image/jpeg",
            "alt_text": "Synthetic front of the home",
            "rights_state": "licensed",
            "idempotency_key": _key("media"),
        },
    )
    assert media.status_code == 201 and media.json()["status"] == "approved"
    malicious = client.post(
        "/api/v2/portfolio/media",
        headers=headers,
        json={
            "space_id": space_id,
            "content": "EICAR-test-string",
            "signature": "EICAR",
            "declared_mime": "image/jpeg",
            "alt_text": "Unsafe file",
            "rights_state": "licensed",
            "idempotency_key": _key("bad-media"),
        },
    )
    assert malicious.status_code == 201 and malicious.json()["status"] == "rejected"
    retired = client.post(
        "/api/v2/portfolio/media/retire",
        headers=headers,
        json={"asset_id": malicious.json()["id"], "idempotency_key": _key("retire")},
    )
    assert retired.status_code == 200 and retired.json()["status"] == "retired"
    preview = client.post("/api/v2/portfolio/snapshots/preview", headers=headers, json={"listing_id": listing_id})
    assert preview.status_code == 200 and preview.json()["noindex"] is True
    assert preview.headers["cache-control"] == "no-store"
    unsafe_copy = client.post(
        "/api/v2/portfolio/snapshots",
        headers=headers,
        json={
            "listing_id": listing_id,
            "expected_version": 1,
            "public_slug": f"phase8-{uuid4().hex[:8]}",
            "description": "No children may apply.",
            "idempotency_key": _key("blocked-copy"),
        },
    )
    assert unsafe_copy.status_code == 422
    slug = f"phase8-{uuid4().hex[:8]}"
    published = client.post(
        "/api/v2/portfolio/snapshots",
        headers=headers,
        json={
            "listing_id": listing_id,
            "expected_version": 1,
            "public_slug": slug,
            "description": "EXAMPLE ONLY. Synthetic listing facts.",
            "idempotency_key": _key("publish"),
        },
    )
    assert published.status_code == 201, published.text
    public = client.get(f"/api/v2/public/listing-snapshots/{slug}")
    assert public.status_code == 200, public.text
    body = public.json()
    assert body["amount_minor"] == 200000
    assert body["estimate_minor"] == 204500
    assert "ledger" in body["estimate_disclaimer"]
    assert "organization_id" not in body and "access_code" not in body and "internal_note" not in body
    detail = client.get(f"/api/v2/listings/{listing_id}")
    assert detail.status_code == 200
    assert detail.json()["estimate_disclaimer"]
    hold = client.post(
        "/api/v2/portfolio/holds",
        headers=headers,
        json={
            "space_id": space_id,
            "reason": "Synthetic temporary hold.",
            "holder_label": "Ann",
            "expires_at": "2001-01-01T00:00:00Z",
            "idempotency_key": _key("hold"),
        },
    )
    assert hold.status_code == 201, hold.text
    released = client.post("/api/v2/portfolio/holds/release-due", headers=headers)
    assert released.status_code == 200 and released.json()["released"] >= 1
    dry = client.post(
        "/api/v2/portfolio/bulk/dry-run",
        headers=headers,
        json={"space_ids": [space_id, str(uuid4())], "amount_minor": 150000},
    )
    assert dry.status_code == 200
    assert dry.json()["applied"] is False
    assert dry.json()["eligible"] and dry.json()["ineligible"]
    blocked_bulk = client.post(
        "/api/v2/portfolio/bulk/apply",
        headers=headers,
        json={"space_ids": [space_id], "amount_minor": 100000, "effective_on": "2026-12-01", "reason": "Material bulk reduction.", "idempotency_key": _key("bulk-block")},
    )
    assert blocked_bulk.status_code == 200
    assert blocked_bulk.json()["results"][0]["applied"] is False
    applied_bulk = client.post(
        "/api/v2/portfolio/bulk/apply",
        headers=headers,
        json={"space_ids": [space_id], "amount_minor": 200000, "effective_on": "2026-12-01", "reason": "Routine bulk confirmation.", "idempotency_key": _key("bulk-apply")},
    )
    assert applied_bulk.status_code == 200, applied_bulk.text
    assert applied_bulk.json()["results"][0]["applied"] is True
    removed = client.post(
        "/api/v2/portfolio/snapshots/unpublish",
        headers=headers,
        json={"public_slug": slug, "idempotency_key": _key("unpublish")},
    )
    assert removed.status_code == 200, removed.text
    hidden = client.get(f"/api/v2/public/listing-snapshots/{slug}")
    assert hidden.status_code == 404
    rolled = client.post(
        "/api/v2/portfolio/snapshots/rollback",
        headers=headers,
        json={"snapshot_id": published.json()["id"], "expected_version": removed.json().get("version", 3), "idempotency_key": _key("rollback")},
    )
    # Unpublish does not return the listing version. Read it from a failed stale rollback if needed.
    if rolled.status_code == 409:
        current = client.get("/api/v2/portfolio/inventory", headers=headers, params={"limit": 100})
        version = next(row["listing_version"] for row in current.json()["records"] if row["listing_id"] == listing_id)
        rolled = client.post(
            "/api/v2/portfolio/snapshots/rollback",
            headers=headers,
            json={"snapshot_id": published.json()["id"], "expected_version": version, "idempotency_key": _key("rollback-2")},
        )
    assert rolled.status_code == 201, rolled.text
    restored = client.get(f"/api/v2/public/listing-snapshots/{slug}")
    assert restored.status_code == 200
    client.post(
        "/api/v2/portfolio/snapshots/unpublish",
        headers=headers,
        json={"public_slug": slug, "idempotency_key": _key("unpublish-2")},
    )
    copied = client.post(
        "/api/v2/portfolio/duplicate",
        headers=headers,
        json={"property_id": property_id, "idempotency_key": _key("duplicate")},
    )
    assert copied.status_code == 201 and copied.json()["copied_listings"] == 0
    stale = client.post(
        "/api/v2/portfolio/archive",
        headers=headers,
        json={"property_id": property_id, "expected_version": 9, "idempotency_key": _key("stale")},
    )
    assert stale.status_code == 409
    archived = client.post(
        "/api/v2/portfolio/archive",
        headers=headers,
        json={"property_id": property_id, "expected_version": 1, "idempotency_key": _key("archive")},
    )
    assert archived.status_code == 200, archived.text
    resident = _auth(_login(client, "resident.synthetic@example.com"))
    denied = client.post(
        "/api/v2/portfolio/prices",
        headers=resident,
        json={"space_id": space_id, "amount_minor": 100, "effective_on": "2026-12-01", "reason": "Resident cannot price.", "idempotency_key": _key("resident")},
    )
    assert denied.status_code == 403
    isolation = _auth(_login(client, "isolation.synthetic@example.com"))
    foreign = client.get("/api/v2/portfolio/inventory", headers=isolation)
    assert foreign.status_code == 200
    assert all(row["property_id"] != property_id for row in foreign.json()["records"])
    with runtime_transaction(_settings(), None, None, uuid4()) as connection:
        leaked = connection.execute(text("SELECT count(*) FROM asking_prices")).scalar()
    assert leaked == 0


def test_runtime_role_has_no_bypass():
    admin = engine_for(_settings().admin_url)
    with admin.connect() as connection:
        role = connection.execute(
            text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'perchpoint_runtime'")
        ).one()
    admin.dispose()
    assert role[0] is False and role[1] is False

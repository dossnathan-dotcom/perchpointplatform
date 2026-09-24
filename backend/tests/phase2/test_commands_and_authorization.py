"""Command, worker, inbox, and authorization failure tests."""
import hashlib
import hmac
import json
import os
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest
from dotenv import load_dotenv
from fastapi.testclient import TestClient
from sqlalchemy import text

load_dotenv()

from foundation.seeds import sid
from perchpoint.db import engine_for, runtime_transaction
from perchpoint.routes import create_app
from perchpoint.settings import Phase2ConfigurationError, Settings


def _settings() -> Settings:
    return Settings.load()


def _admin():
    return engine_for(_settings().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")


def _login(client, email):
    response = client.post("/api/v2/session", json={"email": email, "password": os.environ["PHASE2_DEV_PASSWORD"]})
    assert response.status_code == 200, response.text
    return response.json()["token"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def client():
    return TestClient(create_app())


def test_property_building_space_activity_and_stale_edit(client):
    token = _login(client, "ann.synthetic@example.com")
    created = client.post(
        "/api/v2/properties",
        headers=_auth(token),
        json={"name": "Workflow Court", "property_type": "multifamily", "idempotency_key": "prop-" + uuid4().hex},
    )
    assert created.status_code == 201, created.text
    property_id = created.json()["id"]
    building = client.post(
        "/api/v2/buildings",
        headers=_auth(token),
        json={"property_id": property_id, "name": "Main", "allowed_uses": ["residential", "commercial"], "idempotency_key": "bldg-" + uuid4().hex},
    )
    assert building.status_code == 201, building.text
    residential = client.post(
        "/api/v2/spaces",
        headers=_auth(token),
        json={
            "property_id": property_id,
            "building_id": building.json()["id"],
            "label": "Unit 1",
            "use": "residential",
            "square_feet": 640,
            "idempotency_key": "space-r-" + uuid4().hex,
        },
    )
    commercial = client.post(
        "/api/v2/spaces",
        headers=_auth(token),
        json={
            "property_id": property_id,
            "building_id": building.json()["id"],
            "label": "Shop A",
            "use": "commercial",
            "square_feet": 900,
            "idempotency_key": "space-c-" + uuid4().hex,
        },
    )
    assert residential.status_code == 201 and commercial.status_code == 201
    listed = client.get(f"/api/v2/spaces?building_id={building.json()['id']}", headers=_auth(token))
    assert {item["use"] for item in listed.json()["spaces"]} == {"residential", "commercial"}
    renamed = client.post(
        f"/api/v2/properties/{property_id}",
        headers=_auth(token),
        json={"name": "Workflow Court Renamed", "expected_version": 1, "idempotency_key": "edit-" + uuid4().hex},
    )
    assert renamed.status_code == 200, renamed.text
    stale = client.post(
        f"/api/v2/properties/{property_id}",
        headers=_auth(token),
        json={"name": "Ignored", "expected_version": 1, "idempotency_key": "edit-" + uuid4().hex},
    )
    assert stale.status_code == 409
    transition = client.post(
        f"/api/v2/spaces/{residential.json()['id']}/transition",
        headers=_auth(token),
        json={"dimension": "availability", "value": "offerable", "expected_version": 1, "idempotency_key": "tr-" + uuid4().hex},
    )
    assert transition.status_code == 200, transition.text
    history = client.get(f"/api/v2/activity?resource_id={property_id}", headers=_auth(token))
    assert any(item["summary"] == "property.created" for item in history.json()["activity"])
    assert history.json()["activity"][0]["actor_id"]
    page = client.get("/api/v2/properties?limit=1", headers=_auth(token))
    assert page.json()["limit"] == 1
    assert page.json()["total_count"] >= 1
    isolation = _login(client, "isolation.synthetic@example.com")
    hidden = client.get(f"/api/v2/activity?resource_id={property_id}", headers=_auth(isolation))
    assert hidden.json()["activity"] == []


def test_injected_failure_rolls_back_property_write(client):
    token = _login(client, "ann.synthetic@example.com")
    name = "Rollback " + uuid4().hex[:8]
    os.environ["PHASE2_INJECT_BEFORE_OUTBOX"] = "1"
    try:
        failed = client.post(
            "/api/v2/properties",
            headers=_auth(token),
            json={"name": name, "property_type": "single_family", "idempotency_key": "roll-" + uuid4().hex},
        )
    finally:
        os.environ.pop("PHASE2_INJECT_BEFORE_OUTBOX", None)
    assert failed.status_code == 500
    with runtime_transaction(_settings(), sid("account-phase2-ann"), sid("organization-demo"), uuid4()) as connection:
        count = connection.execute(text("SELECT count(*) FROM properties WHERE name = :name"), {"name": name}).scalar()
    assert count == 0


def test_concurrent_same_key_creates_one_property(client):
    token = _login(client, "ann.synthetic@example.com")
    body = {"name": "Concurrent " + uuid4().hex[:8], "property_type": "single_family", "idempotency_key": "same-" + uuid4().hex}

    def post():
        return TestClient(create_app()).post("/api/v2/properties", headers=_auth(token), json=body)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: post(), range(2)))
    assert sorted(item.status_code for item in results) == [200, 201] or all(item.status_code == 201 for item in results)
    ids = {item.json()["id"] for item in results if item.status_code in {200, 201}}
    assert len(ids) == 1


def test_worker_failure_then_recovery_and_dead_letter():
    admin = _admin()
    org = sid("organization-demo")
    failing = uuid4()
    exhausted = uuid4()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(
            text(
                """
                INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, attempts, available_at)
                VALUES (:org, :id, 'synthetic.delivery', :id, CAST(:payload AS jsonb), 'pending', 0, '1970-01-01')
                """
            ),
            {"org": org, "id": failing, "payload": json.dumps({"fail_once": True, "synthetic": True})},
        )
        connection.execute(
            text(
                """
                INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, attempts, available_at)
                VALUES (:org, :id, 'synthetic.delivery', :id, '{"synthetic": true}', 'pending', 5, '1970-01-02')
                """
            ),
            {"org": org, "id": exhausted},
        )
    admin.dispose()
    client = TestClient(create_app())
    token = _login(client, "ann.synthetic@example.com")
    seen = {}
    for _ in range(8):
        result = client.post("/api/v2/worker/once", headers=_auth(token)).json()
        if result.get("id"):
            seen[result["id"]] = result["status"]
        if result.get("status") == "retry":
            admin = _admin()
            with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
                connection.execute(text("UPDATE outbox SET available_at = '1970-01-01', lease_until = NULL WHERE id = :id"), {"id": failing})
            admin.dispose()
    assert seen.get(str(exhausted)) == "dead_letter"
    assert seen.get(str(failing)) == "delivered"


def test_two_workers_claim_different_rows():
    admin = _admin()
    org = sid("organization-demo")
    first_id, second_id = uuid4(), uuid4()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for item in (first_id, second_id):
            connection.execute(
                text(
                    """
                    INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, attempts, available_at)
                    VALUES (:org, :id, 'synthetic.delivery', :id, '{"synthetic": true}', 'pending', 0, '1960-01-01')
                    """
                ),
                {"org": org, "id": item},
            )
    admin.dispose()
    from perchpoint.commands import claim_and_deliver

    with ThreadPoolExecutor(max_workers=2) as pool:
        claimed = list(pool.map(lambda _: claim_and_deliver(_settings(), "worker-" + uuid4().hex[:4]), range(2)))
    ids = [item.get("id") for item in claimed if item.get("claimed")]
    assert len(ids) == 2 and len(set(ids)) == 2
    admin = _admin()
    with admin.connect() as connection:
        statuses = connection.execute(text("SELECT id, status FROM outbox WHERE id IN (:first, :second)"), {"first": first_id, "second": second_id}).fetchall()
    admin.dispose()
    assert {row.status for row in statuses} <= {"claimed", "delivered", "pending"}
    assert any(row.status != "pending" for row in statuses)


def test_worker_lease_expires_and_is_reclaimed():
    admin = _admin()
    org = sid("organization-demo")
    event_id = uuid4()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(
            text(
                """
                INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, attempts, available_at)
                VALUES (:org, :id, 'synthetic.delivery', :id, '{"synthetic": true, "fail_once": false}', 'pending', 0, '0001-01-01')
                """
            ),
            {"org": org, "id": event_id},
        )
    admin.dispose()
    settings = _settings()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        first = connection.execute(text("SELECT * FROM perchpoint.claim_outbox('worker-a')")).mappings().first()
    assert first["id"] == event_id
    assert first["attempts"] == 1
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        blocked = connection.execute(text("SELECT id FROM perchpoint.claim_outbox('worker-b')")).mappings().all()
    assert all(row["id"] != event_id for row in blocked)
    admin = _admin()
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("UPDATE outbox SET lease_until = now() - interval '1 minute' WHERE id = :id"), {"id": event_id})
    admin.dispose()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        second = connection.execute(text("SELECT * FROM perchpoint.claim_outbox('worker-b')")).mappings().first()
    assert second["id"] == event_id
    assert second["attempts"] == 2
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        status = connection.execute(text("SELECT perchpoint.finish_outbox(:id, true)"), {"id": event_id}).scalar()
    assert status == "delivered"


def test_signed_inbox_dedupe_isolation_and_stale():
    secret = os.environ["PHASE2_WEBHOOK_SECRET"].encode()
    org = str(sid("organization-demo"))
    event = {
        "organization_id": org,
        "provider": "synthetic",
        "account_name": "demo",
        "environment": "development",
        "provider_event_id": "evt-" + uuid4().hex,
        "aggregate_version": 1,
    }
    raw = json.dumps(event).encode()
    signature = hmac.new(secret, raw, hashlib.sha256).hexdigest()
    client = TestClient(create_app())
    first = client.post("/api/v2/inbox/synthetic", content=raw, headers={"x-perchpoint-signature": signature})
    replay = client.post("/api/v2/inbox/synthetic", content=raw, headers={"x-perchpoint-signature": signature})
    assert first.json()["disposition"] == "applied"
    assert replay.json()["disposition"] == "duplicate"
    rejected = client.post("/api/v2/inbox/synthetic", content=raw, headers={"x-perchpoint-signature": "0" * 64})
    assert rejected.status_code == 401
    other = dict(event, environment="production", provider_event_id=event["provider_event_id"])
    other_raw = json.dumps(other).encode()
    other_sig = hmac.new(secret, other_raw, hashlib.sha256).hexdigest()
    isolated = client.post("/api/v2/inbox/synthetic", content=other_raw, headers={"x-perchpoint-signature": other_sig})
    assert isolated.json()["disposition"] == "applied"
    stale = dict(event, provider_event_id="evt-" + uuid4().hex, aggregate_version=0)
    stale_raw = json.dumps(stale).encode()
    stale_sig = hmac.new(secret, stale_raw, hashlib.sha256).hexdigest()
    ignored = client.post("/api/v2/inbox/synthetic", content=stale_raw, headers={"x-perchpoint-signature": stale_sig})
    assert ignored.json()["disposition"] == "ignored_stale"


def test_expired_membership_and_production_auth_refused(client):
    expired = client.post("/api/v2/session", json={"email": "expired.synthetic@example.com", "password": os.environ["PHASE2_DEV_PASSWORD"]})
    assert expired.status_code == 403
    previous = os.environ["PHASE2_LOCAL_AUTH"]
    os.environ["PHASE2_LOCAL_AUTH"] = "production"
    try:
        with pytest.raises(Phase2ConfigurationError):
            Settings.load()
    finally:
        os.environ["PHASE2_LOCAL_AUTH"] = previous


def test_reference_path_listing_inquiry_and_isolation(client):
    token = _login(client, "ann.synthetic@example.com")
    headers = _auth(token)
    created = client.post("/api/v2/properties", headers=headers, json={"name": "Path Court", "property_type": "mixed_use", "idempotency_key": "path-p-" + uuid4().hex})
    assert created.status_code == 201, created.text
    property_id = created.json()["id"]
    building = client.post("/api/v2/buildings", headers=headers, json={"property_id": property_id, "name": "House", "allowed_uses": ["residential"], "idempotency_key": "path-b-" + uuid4().hex})
    space = client.post(
        "/api/v2/spaces",
        headers=headers,
        json={"property_id": property_id, "building_id": building.json()["id"], "label": "Unit A", "use": "residential", "square_feet": 800, "idempotency_key": "path-s-" + uuid4().hex},
    )
    assert space.status_code == 201, space.text
    offered = client.post(
        f"/api/v2/spaces/{space.json()['id']}/transition",
        headers=headers,
        json={"dimension": "availability", "value": "offerable", "expected_version": 1, "idempotency_key": "path-t-" + uuid4().hex},
    )
    assert offered.status_code == 200, offered.text
    listing = client.post(
        "/api/v2/listings",
        headers=headers,
        json={
            "space_id": space.json()["id"],
            "property_name": "Path Court",
            "label": "Unit A",
            "use": "residential",
            "municipality": "Cincinnati",
            "state": "OH",
            "amount_minor": 145000,
            "currency": "USD",
            "idempotency_key": "path-l-" + uuid4().hex,
        },
    )
    assert listing.status_code == 201, listing.text
    hidden = client.get("/api/v2/listings")
    assert all(item["listing_id"] != listing.json()["id"] for item in hidden.json()["listings"])
    published = client.post(
        f"/api/v2/listings/{listing.json()['id']}/publication",
        headers=headers,
        json={"publication": "published", "expected_version": 1, "idempotency_key": "path-pub-" + uuid4().hex},
    )
    assert published.status_code == 200, published.text
    visible = client.get("/api/v2/listings")
    match = next(item for item in visible.json()["listings"] if item["listing_id"] == listing.json()["id"])
    assert "organization_id" not in match
    key = "path-inq-" + uuid4().hex
    inquiry = client.post("/api/v2/inquiries", json={"listing_id": listing.json()["id"], "name": "Path Guest", "email": "path@example.com", "intent": "showing", "message": "Example", "idempotency_key": key})
    replay = client.post("/api/v2/inquiries", json={"listing_id": listing.json()["id"], "name": "Path Guest", "email": "path@example.com", "intent": "showing", "message": "Example", "idempotency_key": key})
    assert inquiry.status_code == 201 and replay.json()["inquiry_id"] == inquiry.json()["inquiry_id"]
    queue = client.get("/api/v2/inquiries", headers=headers)
    assert any(item["id"] == inquiry.json()["inquiry_id"] for item in queue.json()["inquiries"])
    triaged = client.post(
        f"/api/v2/inquiries/{inquiry.json()['inquiry_id']}/triage",
        headers=headers,
        json={"decision": "assigned", "expected_version": 1, "idempotency_key": "path-tri-" + uuid4().hex},
    )
    stale = client.post(
        f"/api/v2/inquiries/{inquiry.json()['inquiry_id']}/triage",
        headers=headers,
        json={"decision": "closed_not_pursuing", "expected_version": 1, "idempotency_key": "path-stale-" + uuid4().hex},
    )
    note = client.post(
        f"/api/v2/inquiries/{inquiry.json()['inquiry_id']}/notes",
        headers=headers,
        json={"body": "Called back.", "idempotency_key": "path-note-" + uuid4().hex},
    )
    assert triaged.status_code == 200 and stale.status_code == 409 and note.status_code == 201
    history = client.get(f"/api/v2/activity?resource_id={property_id}", headers=headers)
    assert history.json()["activity"]
    worker = client.post("/api/v2/worker/once", headers=headers)
    assert worker.status_code == 200
    isolation = _login(client, "isolation.synthetic@example.com")
    denied = client.get("/api/v2/inquiries", headers=_auth(isolation))
    assert all(item["id"] != inquiry.json()["inquiry_id"] for item in denied.json()["inquiries"])
    forged = client.get("/api/v2/inquiries", headers={**_auth(isolation), "X-Organization": str(sid("organization-demo"))})
    assert all(item["id"] != inquiry.json()["inquiry_id"] for item in forged.json()["inquiries"])


def test_empty_database_migration_and_repeatable_seed():
    admin = engine_for(_settings().admin_url.rsplit("/", 1)[0] + "/postgres")
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        exists = connection.execute(text("SELECT 1 FROM pg_database WHERE datname = 'perchpoint_phase2_empty'")).scalar()
        if not exists:
            connection.execute(text("CREATE DATABASE perchpoint_phase2_empty"))
        connection.execute(text("GRANT CONNECT, CREATE ON DATABASE perchpoint_phase2_empty TO perchpoint_migrator"))
    admin.dispose()
    empty = engine_for(_settings().admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2_empty")
    with empty.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("GRANT ALL ON SCHEMA public TO perchpoint_migrator"))
        connection.execute(text("GRANT perchpoint_definer TO perchpoint_migrator"))
    empty.dispose()
    migrator = os.environ["PHASE2_MIGRATOR_URL"]
    os.environ["PHASE2_MIGRATOR_URL"] = migrator.rsplit("/", 1)[0] + "/perchpoint_phase2_empty"
    try:
        from alembic.config import Config
        from alembic import command

        config = Config("alembic.ini")
        command.upgrade(config, "head")
    finally:
        os.environ["PHASE2_MIGRATOR_URL"] = migrator
    from perchpoint.seed import seed

    seed(database="perchpoint_phase2_empty")
    seed(database="perchpoint_phase2_empty")
    with empty.connect() as connection:
        count = connection.execute(text("SELECT count(*) FROM properties WHERE id = :id"), {"id": sid("property-elm")}).scalar()
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    empty.dispose()
    assert count == 1
    assert revision == "0005_listing_notes"


def test_pooled_connection_does_not_keep_previous_scope():
    elm = sid("property-elm")
    with runtime_transaction(_settings(), sid("account-phase2-ann"), sid("organization-demo"), uuid4()) as connection:
        visible = connection.execute(text("SELECT count(*) FROM properties WHERE id = :id"), {"id": elm}).scalar()
    with runtime_transaction(_settings(), None, None, uuid4()) as connection:
        leaked = connection.execute(text("SELECT count(*) FROM properties WHERE id = :id"), {"id": elm}).scalar()
    assert visible == 1
    assert leaked == 0

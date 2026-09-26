"""Disposable Compose checks for project perchpoint-phase3. Prints no secrets."""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
API = "http://127.0.0.1:8000/api/v2"
WEB = "http://127.0.0.1:3000"
PROJECT = "perchpoint-phase3"
POSTGRES = f"{PROJECT}-postgres-1"


def req(method: str, url: str, body: dict | None = None, headers: dict | None = None) -> tuple[int, dict | str]:
    data = None if body is None else json.dumps(body).encode()
    request = urllib.request.Request(url, data=data, method=method)
    request.add_header("content-type", "application/json")
    for key, value in (headers or {}).items():
        request.add_header(key, value)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        status = exc.code
    try:
        parsed: dict | str = json.loads(raw)
    except json.JSONDecodeError:
        parsed = raw
    return status, parsed


def psql(sql: str) -> str:
    completed = subprocess.run(
        ["docker", "exec", POSTGRES, "psql", "-U", "postgres", "-d", "perchpoint_phase2", "-v", "ON_ERROR_STOP=1", "-At", "-c", sql],
        check=True,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def compose_python(source: str, extra_env: dict | None = None) -> str:
    command = [
        "docker",
        "compose",
        "-p",
        PROJECT,
        "run",
        "--rm",
        "--no-deps",
        "--entrypoint",
        "python",
    ]
    for key, value in (extra_env or {}).items():
        command.extend(["-e", f"{key}={value}"])
    command.extend(["api", "-c", source])
    completed = subprocess.run(command, cwd=ROOT, check=True, capture_output=True, text=True)
    return completed.stdout.strip()


def counts() -> dict[str, str]:
    raw = psql(
        """
        SELECT 'organizations', count(*) FROM organizations
        UNION ALL SELECT 'properties', count(*) FROM properties
        UNION ALL SELECT 'buildings', count(*) FROM buildings
        UNION ALL SELECT 'spaces', count(*) FROM spaces
        UNION ALL SELECT 'listings', count(*) FROM listings
        UNION ALL SELECT 'memberships', count(*) FROM memberships
        UNION ALL SELECT 'elm', count(*) FROM properties WHERE name LIKE 'Example Elm Court%'
        UNION ALL SELECT 'expired', count(*) FROM memberships WHERE ended_at IS NOT NULL AND ended_at <= now()
        """
    )
    return dict(line.split("|") for line in raw.splitlines())


def percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int(round((len(ordered) - 1) * fraction))))
    return ordered[index]


def timed(method: str, url: str, headers: dict | None, warmup: int, measured: int) -> dict[str, float | int]:
    for _ in range(warmup):
        status, _ = req(method, url, headers=headers)
        if status != 200:
            raise SystemExit(f"warmup failed {url} {status}")
    samples: list[float] = []
    errors = 0
    for _ in range(measured):
        started = time.perf_counter()
        status, _ = req(method, url, headers=headers)
        samples.append((time.perf_counter() - started) * 1000)
        if status != 200:
            errors += 1
    return {
        "warmup": warmup,
        "measured": measured,
        "p50": round(percentile(samples, 0.50), 2),
        "p95": round(percentile(samples, 0.95), 2),
        "max": round(max(samples), 2),
        "errors": errors,
    }


def main() -> None:
    password = os.environ["PHASE2_DEV_PASSWORD"]
    before = counts()
    print("seed_before", json.dumps(before))
    subprocess.run(["docker", "compose", "-p", PROJECT, "run", "--rm", "--no-deps", "seed"], cwd=ROOT, check=True)
    after = counts()
    print("seed_after", json.dumps(after))
    if before != after or before.get("elm") != "1":
        raise SystemExit("seed was not idempotent")

    status, listings = req("GET", f"{API}/listings")
    assert status == 200 and isinstance(listings, dict)
    public = listings["listings"][0]
    assert "organization_id" not in public and "space_id" not in public
    status, detail = req("GET", f"{API}/listings/{public['listing_id']}")
    assert status == 200 and detail["listing_id"] == public["listing_id"]
    web_status, web_listings = req("GET", f"{WEB}/api/v2/listings")
    assert web_status == 200 and web_listings["listings"]
    key = "inquiry-" + uuid.uuid4().hex
    body = {
        "listing_id": public["listing_id"],
        "name": "Clean Room Guest",
        "email": "clean-room@example.com",
        "intent": "showing",
        "message": "Synthetic only",
        "idempotency_key": key,
    }
    created_status, created = req("POST", f"{API}/inquiries", body)
    replay_status, replay = req("POST", f"{API}/inquiries", body)
    conflict_status, _ = req("POST", f"{API}/inquiries", {**body, "message": "different"})
    assert created_status == 201 and replay_status == 201 and replay["inquiry_id"] == created["inquiry_id"] and conflict_status == 409

    missing_status, _ = req("GET", f"{API}/properties")
    assert missing_status == 401
    status, session = req("POST", f"{API}/session", {"email": "ann.synthetic@example.com", "password": password})
    assert status == 200 and session["synthetic"] is True
    token = session["token"]
    auth = {"Authorization": f"Bearer {token}"}
    status, properties = req("GET", f"{API}/properties", headers=auth)
    assert status == 200 and any("Elm Court" in item["name"] for item in properties["properties"])
    forged_status, forged = req(
        "GET",
        f"{API}/properties",
        headers={**auth, "X-Organization": "00000000-0000-0000-0000-000000000099"},
    )
    assert forged_status == 200 and any("Elm Court" in item["name"] for item in forged["properties"])
    expired_status, _ = req("POST", f"{API}/session", {"email": "expired.synthetic@example.com", "password": password})
    assert expired_status == 403
    other_status, other = req("POST", f"{API}/session", {"email": "isolation.synthetic@example.com", "password": password})
    assert other_status == 200
    other_auth = {"Authorization": f"Bearer {other['token']}"}
    hidden_status, hidden = req("GET", f"{API}/properties", headers=other_auth)
    assert hidden_status == 200 and all("Elm Court" not in item["name"] for item in hidden["properties"])

    stamp = uuid.uuid4().hex[:8]
    created_status, created_property = req(
        "POST",
        f"{API}/properties",
        {"name": f"Clean Room {stamp}", "property_type": "multifamily", "idempotency_key": "prop-" + uuid.uuid4().hex},
        auth,
    )
    assert created_status == 201, created_property
    property_id = created_property["id"]
    denied_status, _ = req(
        "POST",
        f"{API}/properties/{property_id}",
        {"name": "Stolen", "expected_version": 1, "idempotency_key": "steal-" + uuid.uuid4().hex},
        other_auth,
    )
    assert denied_status in {403, 404}
    renamed_status, renamed = req(
        "POST",
        f"{API}/properties/{property_id}",
        {"name": f"Clean Room {stamp} renamed", "expected_version": 1, "idempotency_key": "edit-" + uuid.uuid4().hex},
        auth,
    )
    assert renamed_status == 200
    stale_status, _ = req(
        "POST",
        f"{API}/properties/{property_id}",
        {"name": "Stale", "expected_version": 1, "idempotency_key": "stale-" + uuid.uuid4().hex},
        auth,
    )
    assert stale_status == 409
    building_status, building = req(
        "POST",
        f"{API}/buildings",
        {
            "property_id": property_id,
            "name": f"House {stamp}",
            "allowed_uses": ["residential", "commercial"],
            "idempotency_key": "bldg-" + uuid.uuid4().hex,
        },
        auth,
    )
    assert building_status == 201
    residential_status, residential = req(
        "POST",
        f"{API}/spaces",
        {
            "property_id": property_id,
            "building_id": building["id"],
            "label": f"Unit {stamp}",
            "use": "residential",
            "square_feet": 640,
            "idempotency_key": "space-r-" + uuid.uuid4().hex,
        },
        auth,
    )
    commercial_status, commercial = req(
        "POST",
        f"{API}/spaces",
        {
            "property_id": property_id,
            "building_id": building["id"],
            "label": f"Shop {stamp}",
            "use": "commercial",
            "square_feet": 900,
            "idempotency_key": "space-c-" + uuid.uuid4().hex,
        },
        auth,
    )
    assert residential_status == 201 and commercial_status == 201
    offer_status, _ = req(
        "POST",
        f"{API}/spaces/{residential['id']}/transition",
        {"dimension": "availability", "value": "offerable", "expected_version": 1, "idempotency_key": "offer-" + uuid.uuid4().hex},
        auth,
    )
    assert offer_status == 200
    listing_status, listing = req(
        "POST",
        f"{API}/listings",
        {
            "space_id": residential["id"],
            "property_name": f"Clean Room {stamp}",
            "label": f"Unit {stamp}",
            "use": "residential",
            "municipality": "Cincinnati",
            "state": "OH",
            "amount_minor": 150000,
            "currency": "USD",
            "idempotency_key": "list-" + uuid.uuid4().hex,
        },
        auth,
    )
    assert listing_status == 201 and listing["publication"] == "unpublished"
    published_status, published = req(
        "POST",
        f"{API}/listings/{listing['id']}/publication",
        {"publication": "published", "expected_version": 1, "idempotency_key": "pub-" + uuid.uuid4().hex},
        auth,
    )
    assert published_status == 200
    status, visible = req("GET", f"{API}/listings")
    assert any(item["property_name"] == f"Clean Room {stamp}" for item in visible["listings"])
    restricted_status, _ = req(
        "POST",
        f"{API}/listings/{listing['id']}/publication",
        {"publication": "restricted", "expected_version": published["version"], "idempotency_key": "restrict-" + uuid.uuid4().hex},
        auth,
    )
    assert restricted_status == 200
    status, hidden_public = req("GET", f"{API}/listings")
    assert all(item["listing_id"] != listing["id"] for item in hidden_public["listings"])
    note_status, _ = req(
        "POST",
        f"{API}/inquiries/{created['inquiry_id']}/notes",
        {"body": "Synthetic internal note", "idempotency_key": "note-" + uuid.uuid4().hex},
        auth,
    )
    triage_status, _ = req(
        "POST",
        f"{API}/inquiries/{created['inquiry_id']}/triage",
        {"decision": "assigned", "expected_version": 1, "idempotency_key": "triage-" + uuid.uuid4().hex},
        auth,
    )
    assert note_status == 201 and triage_status == 200
    activity_status, activity = req("GET", f"{API}/activity?resource_id={property_id}", headers=auth)
    assert activity_status == 200 and any(item["summary"] == "property.created" for item in activity["activity"])
    other_activity_status, other_activity = req("GET", f"{API}/activity?resource_id={property_id}", headers=other_auth)
    assert other_activity_status == 200 and other_activity["activity"] == []
    audit_count = psql("SELECT count(*) FROM audit_events")
    outbox_count = psql("SELECT count(*) FROM outbox")
    print("journey_ok", json.dumps({"audit_events": audit_count, "outbox": outbox_count, "stamp": stamp}))

    owners = psql("SELECT DISTINCT tableowner FROM pg_tables WHERE schemaname = 'public' ORDER BY 1")
    print("table_owners", owners.replace("\n", ","))
    runtime_deny = compose_python(
        """
from sqlalchemy import text
from perchpoint.db import engine_for
from perchpoint.settings import Settings
engine = engine_for(Settings.load().runtime_url)
try:
    with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("ALTER TABLE properties DISABLE ROW LEVEL SECURITY"))
    print("allowed")
except Exception:
    print("denied")
finally:
    engine.dispose()
"""
    )
    print("runtime_rls", runtime_deny)
    if "denied" not in runtime_deny:
        raise SystemExit("runtime role disabled RLS")
    audit_deny = compose_python(
        """
from sqlalchemy import text
from perchpoint.db import engine_for
from perchpoint.settings import Settings
from uuid import uuid4
from perchpoint.db import runtime_transaction
from foundation.seeds import sid
settings = Settings.load()
try:
    with runtime_transaction(settings, sid("account-phase2-ann"), sid("organization-demo"), uuid4()) as connection:
        connection.execute(text("UPDATE audit_events SET action = 'tamper'"))
    print("allowed")
except Exception:
    print("denied")
"""
    )
    print("audit_immutable", audit_deny)
    pool = compose_python(
        """
from uuid import uuid4
from sqlalchemy import text
from foundation.seeds import sid
from perchpoint.db import runtime_transaction
from perchpoint.settings import Settings
settings = Settings.load()
elm = sid("property-elm")
with runtime_transaction(settings, sid("account-phase2-ann"), sid("organization-demo"), uuid4()) as connection:
    visible = connection.execute(text("SELECT count(*) FROM properties WHERE id = :id"), {"id": elm}).scalar()
with runtime_transaction(settings, None, None, uuid4()) as connection:
    leaked = connection.execute(text("SELECT count(*) FROM properties WHERE id = :id"), {"id": elm}).scalar()
print(f"visible={visible} leaked={leaked}")
"""
    )
    print("pool", pool)
    before_fail = psql("SELECT count(*) FROM properties")
    before_audit = psql("SELECT count(*) FROM audit_events")
    before_outbox = psql("SELECT count(*) FROM outbox")
    injected = compose_python(
        """
from uuid import uuid4
from perchpoint.commands import create_property
from perchpoint.settings import Settings
from foundation.seeds import sid
try:
    create_property(Settings.load(), sid("account-phase2-ann"), sid("organization-demo"), {"name": "Injected Rollback Court", "property_type": "single_family"}, "inject-" + uuid4().hex, uuid4())
    print("allowed")
except Exception:
    print("rolled_back")
""",
        {"PHASE2_INJECT_BEFORE_OUTBOX": "1"},
    )
    after_fail = psql("SELECT count(*) FROM properties")
    after_audit = psql("SELECT count(*) FROM audit_events")
    after_outbox = psql("SELECT count(*) FROM outbox")
    print("injected", injected, "properties", before_fail, after_fail, "audit", before_audit, after_audit, "outbox", before_outbox, after_outbox)
    if "rolled_back" not in injected or before_fail != after_fail or before_audit != after_audit or before_outbox != after_outbox:
        raise SystemExit("injected failure left a partial write")

    lease = compose_python(
        """
import json
from uuid import uuid4
from sqlalchemy import text
from foundation.seeds import sid
from perchpoint.db import engine_for, runtime_transaction
from perchpoint.settings import Settings
settings = Settings.load()
org = sid("organization-demo")
event_id = uuid4()
admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
    connection.execute(text(\"\"\"
        INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, attempts, available_at)
        VALUES (:org, :id, 'synthetic.delivery', :id, '{\\"synthetic\\": true}', 'pending', 0, '1970-01-01')
    \"\"\"), {"org": org, "id": event_id})
admin.dispose()
with runtime_transaction(settings, None, None, uuid4()) as connection:
    first = connection.execute(text("SELECT * FROM perchpoint.claim_outbox('worker-a')")).mappings().first()
with runtime_transaction(settings, None, None, uuid4()) as connection:
    blocked = connection.execute(text("SELECT id FROM perchpoint.claim_outbox('worker-b')")).mappings().all()
admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
    connection.execute(text("UPDATE outbox SET lease_until = now() - interval '1 minute' WHERE id = :id"), {"id": event_id})
admin.dispose()
with runtime_transaction(settings, None, None, uuid4()) as connection:
    second = connection.execute(text("SELECT * FROM perchpoint.claim_outbox('worker-b')")).mappings().first()
with runtime_transaction(settings, None, None, uuid4()) as connection:
    status = connection.execute(text("SELECT perchpoint.finish_outbox(:id, true)"), {"id": event_id}).scalar()
blocked_same = any(row["id"] == event_id for row in blocked)
print(json.dumps({"first_attempts": first["attempts"], "blocked_same": blocked_same, "second_attempts": second["attempts"], "status": status, "same_row": str(first["id"]) == str(second["id"])}))
"""
    )
    print("lease", lease)
    dead = compose_python(
        """
import json
from uuid import uuid4
from sqlalchemy import text
from foundation.seeds import sid
from perchpoint.commands import claim_and_deliver
from perchpoint.db import engine_for
from perchpoint.settings import Settings
settings = Settings.load()
org = sid("organization-demo")
exhausted = uuid4()
failing = uuid4()
admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
    connection.execute(text(\"\"\"
        INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, attempts, available_at)
        VALUES (:org, :id, 'synthetic.delivery', :id, '{\\"fail_once\\": true, \\"synthetic\\": true}', 'pending', 0, '1970-01-01')
    \"\"\"), {"org": org, "id": failing})
    connection.execute(text(\"\"\"
        INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, attempts, available_at)
        VALUES (:org, :id, 'synthetic.delivery', :id, '{\\"synthetic\\": true}', 'pending', 5, '1970-01-02')
    \"\"\"), {"org": org, "id": exhausted})
admin.dispose()
seen = {}
for _ in range(6):
    result = claim_and_deliver(settings, "clean-room-worker")
    if result.get("id"):
        seen[result["id"]] = result["status"]
    if result.get("status") == "retry":
        admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text("UPDATE outbox SET available_at = '1970-01-01', lease_until = NULL WHERE id = :id"), {"id": failing})
        admin.dispose()
print(json.dumps({"exhausted": seen.get(str(exhausted)), "failing": seen.get(str(failing)), "exactly_once": False}))
"""
    )
    print("dead_letter", dead)

    listing_id = public["listing_id"]
    inquiry_id = created["inquiry_id"]
    print("perf_listings", json.dumps(timed("GET", f"{API}/listings", None, 3, 20)))
    print("perf_detail", json.dumps(timed("GET", f"{API}/listings/{listing_id}", None, 3, 20)))
    print("perf_properties", json.dumps(timed("GET", f"{API}/properties", auth, 3, 20)))
    print("perf_inquiries", json.dumps(timed("GET", f"{API}/inquiries", auth, 3, 20)))
    print("perf_inquiry", json.dumps(timed("GET", f"{API}/inquiries/{inquiry_id}", auth, 3, 20)))
    print("perf_activity", json.dumps(timed("GET", f"{API}/activity?resource_id={property_id}", auth, 3, 20)))
    print("cardinalities", json.dumps(counts() | {"audit_events": psql("SELECT count(*) FROM audit_events"), "outbox": psql("SELECT count(*) FROM outbox"), "inquiries": psql("SELECT count(*) FROM inquiries")}))
    print("clean_room_ok")


if __name__ == "__main__":
    main()

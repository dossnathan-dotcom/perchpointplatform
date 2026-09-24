"""Isolated benchmark load on the development database. Rows are removed afterward."""
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import text

from foundation.seeds import sid
from perchpoint.db import engine_for
from perchpoint.settings import Settings

load_dotenv()

INSERT = """
INSERT INTO properties (organization_id, id, name, property_type)
SELECT %(org)s, gen_random_uuid(), 'Bench ' || g, CASE WHEN mod(g, 5) = 0 THEN 'mixed_use' ELSE 'multifamily' END
FROM generate_series(1, 1000) AS g;

INSERT INTO buildings (organization_id, id, property_id, name, allowed_uses)
SELECT p.organization_id, gen_random_uuid(), p.id, 'Bench building ' || p.name, ARRAY['residential','commercial']
FROM properties p WHERE p.name LIKE ('Bench ' || chr(37));

INSERT INTO spaces (organization_id, id, property_id, building_id, label, use, square_feet)
SELECT b.organization_id, gen_random_uuid(), b.property_id, b.id,
       'Bench ' || b.name || ' ' || kind.use, kind.use, 700
FROM buildings b
CROSS JOIN (VALUES ('residential'), ('commercial')) AS kind(use)
WHERE b.name LIKE ('Bench building ' || chr(37));

INSERT INTO space_states (
  organization_id, id, space_id, condition, occupancy, availability, publication,
  maintenance_restriction, legal_restriction, version, current
)
SELECT s.organization_id, gen_random_uuid(), s.id, 'rent_ready', 'vacant',
       CASE WHEN s.use = 'residential' THEN 'offerable' ELSE 'withheld' END,
       'unpublished', 'none', 'none', 1, true
FROM spaces s WHERE s.label LIKE ('Bench ' || chr(37));

INSERT INTO listings (
  organization_id, id, space_id, publication, availability, property_name, label, use,
  municipality, state, amount_minor, currency, version
)
SELECT s.organization_id, gen_random_uuid(), s.id,
       (ARRAY['published','unpublished','restricted'])[1 + mod((row_number() OVER ())::int, 3)],
       CASE WHEN s.use = 'residential' THEN 'offerable' ELSE 'withheld' END,
       'Bench listing', s.label, s.use, 'Cincinnati', 'OH', 120000, 'USD', 1
FROM spaces s WHERE s.label LIKE ('Bench ' || chr(37)) AND s.use = 'residential'
LIMIT 1000;

INSERT INTO inquiries (
  organization_id, id, listing_id, name, email, intent, message, status, version, received_at
)
SELECT l.organization_id, gen_random_uuid(), l.id, 'Bench guest', 'bench@example.com', 'showing',
       'benchmark', 'open', 1, now()
FROM listings l WHERE l.property_name = 'Bench listing'
LIMIT 1000;

INSERT INTO activity (organization_id, id, resource_type, resource_id, summary, occurred_at, actor_id)
SELECT p.organization_id, gen_random_uuid(), 'record', p.id, 'bench', now(), %(actor)s
FROM properties p
CROSS JOIN generate_series(1, 250) AS g
WHERE p.name LIKE ('Bench ' || chr(37));
"""

DELETE = """
DELETE FROM activity WHERE summary = 'bench';
DELETE FROM inquiries WHERE name = 'Bench guest';
DELETE FROM listings WHERE property_name = 'Bench listing';
DELETE FROM space_states WHERE space_id IN (SELECT id FROM spaces WHERE label LIKE ('Bench ' || chr(37)));
DELETE FROM spaces WHERE label LIKE ('Bench ' || chr(37));
DELETE FROM buildings WHERE name LIKE ('Bench building ' || chr(37));
DELETE FROM properties WHERE name LIKE ('Bench ' || chr(37));
"""


def explain(connection, org, actor, sql):
    transaction = connection.begin()
    connection.execute(
        text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true), set_config('app.request_id', :request, true)"),
        {"actor": str(actor), "org": str(org), "request": str(uuid4())},
    )
    rows = connection.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + sql)).scalars().all()
    transaction.rollback()
    return rows


def concurrent_public(runtime, org, actor, sql):
    def once():
        started = time.perf_counter()
        with runtime.connect() as connection:
            transaction = connection.begin()
            connection.execute(
                text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true), set_config('app.request_id', :request, true)"),
                {"actor": str(actor), "org": str(org), "request": str(uuid4())},
            )
            connection.execute(text(sql))
            transaction.rollback()
        return (time.perf_counter() - started) * 1000

    with ThreadPoolExecutor(max_workers=4) as pool:
        samples = list(pool.map(lambda _: once(), range(8)))
    ordered = sorted(samples)
    return statistics.median(ordered), ordered[max(int(len(ordered) * 0.95) - 1, 0)], max(ordered)


def measure(connection, org, actor, sql):
    samples = []
    for _ in range(11):
        started = time.perf_counter()
        transaction = connection.begin()
        connection.execute(
            text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true), set_config('app.request_id', :request, true)"),
            {"actor": str(actor), "org": str(org), "request": str(uuid4())},
        )
        connection.execute(text(sql))
        transaction.rollback()
        samples.append((time.perf_counter() - started) * 1000)
    ordered = sorted(samples[1:])
    return statistics.median(ordered), ordered[max(int(len(ordered) * 0.95) - 1, 0)], max(ordered)


def main():
    settings = Settings.load()
    admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/perchpoint_phase2")
    runtime = engine_for(settings.runtime_url)
    org = sid("organization-demo")
    actor = sid("account-phase2-ann")
    with admin.begin() as connection:
        for statement in INSERT.split(";"):
            if statement.strip():
                connection.exec_driver_sql(statement, {"org": org, "actor": actor})
        counts = connection.execute(text("""
            SELECT
              (SELECT count(*) FROM properties WHERE name LIKE ('Bench ' || chr(37))),
              (SELECT count(*) FROM buildings WHERE name LIKE ('Bench building ' || chr(37))),
              (SELECT count(*) FROM spaces WHERE label LIKE ('Bench ' || chr(37))),
              (SELECT count(*) FROM listings WHERE property_name = 'Bench listing'),
              (SELECT count(*) FROM inquiries WHERE name = 'Bench guest'),
              (SELECT count(*) FROM activity WHERE summary = 'bench')
        """)).one()
        sample_property = connection.execute(text("SELECT id FROM properties WHERE name LIKE ('Bench ' || chr(37)) LIMIT 1")).scalar()
        sample_listing = connection.execute(text("SELECT id FROM listings WHERE property_name = 'Bench listing' AND publication = 'published' LIMIT 1")).scalar()
        sample_inquiry = connection.execute(text("SELECT id FROM inquiries WHERE name = 'Bench guest' LIMIT 1")).scalar()
    try:
        with runtime.connect() as connection:
            queries = {
                "property_list": "SELECT id, name FROM properties WHERE name LIKE ('Bench ' || chr(37)) ORDER BY id LIMIT 50",
                "property_hierarchy": "SELECT b.id, s.id FROM buildings b JOIN spaces s ON s.building_id = b.id WHERE b.property_id = '%s'" % sample_property,
                "inquiry_queue": "SELECT id, status FROM inquiries WHERE name = 'Bench guest' ORDER BY received_at DESC LIMIT 50",
                "inquiry_detail": "SELECT id, status, message FROM inquiries WHERE id = '%s'" % sample_inquiry,
                "activity_timeline": "SELECT id, summary FROM activity WHERE resource_id = '%s' AND summary = 'bench' ORDER BY occurred_at DESC LIMIT 50" % sample_property,
                "public_listings": "SELECT listing_id FROM perchpoint.published_listings() WHERE property_name = 'Bench listing'",
                "public_listing_detail": "SELECT listing_id, label FROM perchpoint.published_listings() WHERE listing_id = '%s'" % sample_listing,
            }
            print("counts", tuple(counts))
            print("warmup 1 measured 10 query_count 10 plus one context statement each")
            for name, sql in queries.items():
                p50, p95, maximum = measure(connection, org, actor, sql)
                print(f"{name} p50_ms {p50:.2f} p95_ms {p95:.2f} max_ms {maximum:.2f}")
                for line in explain(connection, org, actor, sql):
                    if "Scan" in line or "Index" in line or "Execution Time" in line:
                        print(f"plan {name}: {line.strip()}")
            p50, p95, maximum = concurrent_public(runtime, org, actor, queries["public_listings"])
            print(f"concurrent_public_4x2 p50_ms {p50:.2f} p95_ms {p95:.2f} max_ms {maximum:.2f}")
    finally:
        with admin.begin() as connection:
            connection.execute(text(DELETE))
            leftover = connection.execute(text("SELECT count(*) FROM properties WHERE name LIKE ('Bench ' || chr(37))")).scalar()
        print("leftover_properties", leftover)
    admin.dispose()
    runtime.dispose()


if __name__ == "__main__":
    main()

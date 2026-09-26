"""Design-mix benchmark on a disposable database. The development database is not loaded."""
import os
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from foundation.seeds import sid
from perchpoint.db import engine_for
from perchpoint.settings import Settings

load_dotenv()

BENCH = "perchpoint_phase2_bench"


def engine(url, **kwargs):
    if url.startswith("postgresql://"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]
    return create_engine(url, pool_pre_ping=True, **kwargs)


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


def explain(connection, org, actor, sql):
    transaction = connection.begin()
    connection.execute(
        text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true), set_config('app.request_id', :request, true)"),
        {"actor": str(actor), "org": str(org), "request": str(uuid4())},
    )
    rows = connection.execute(text("EXPLAIN (ANALYZE, BUFFERS) " + sql)).scalars().all()
    transaction.rollback()
    return rows


def concurrent(runtime, org, actor, sql, workers):
    def once(_index):
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

    with ThreadPoolExecutor(max_workers=workers) as pool:
        warmup = list(pool.map(once, range(workers)))
        samples = list(pool.map(once, range(workers)))
    ordered = sorted(samples)
    return statistics.median(ordered), ordered[max(int(len(ordered) * 0.95) - 1, 0)], max(ordered), max(warmup)


def main():
    settings = Settings.load()
    root = settings.admin_url.rsplit("/", 1)[0]
    admin = engine(root + "/postgres")
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text(f"DROP DATABASE IF EXISTS {BENCH} WITH (FORCE)"))
        connection.execute(text(f"CREATE DATABASE {BENCH}"))
        connection.execute(text(f"GRANT CONNECT, CREATE ON DATABASE {BENCH} TO perchpoint_migrator"))
        connection.execute(text(f"GRANT CONNECT ON DATABASE {BENCH} TO perchpoint_runtime"))
    admin.dispose()
    bench_admin = engine(root + "/" + BENCH)
    with bench_admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("GRANT ALL ON SCHEMA public TO perchpoint_migrator"))
        connection.execute(text("GRANT perchpoint_definer TO perchpoint_migrator"))
    version = bench_admin.connect().execute(text("SHOW server_version")).scalar()
    migrator = os.environ["PHASE2_MIGRATOR_URL"]
    os.environ["PHASE2_MIGRATOR_URL"] = migrator.rsplit("/", 1)[0] + "/" + BENCH
    try:
        from alembic.config import Config
        from alembic import command

        command.upgrade(Config("alembic.ini"), "head")
    finally:
        os.environ["PHASE2_MIGRATOR_URL"] = migrator
    with bench_admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO perchpoint_definer"))
        connection.execute(text("GRANT USAGE, CREATE ON SCHEMA perchpoint TO perchpoint_definer"))
        connection.execute(text("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA perchpoint TO perchpoint_definer"))
        for name in (
            "actor_in_org(uuid)",
            "published_listings()",
            "login_material(text)",
            "current_membership(uuid)",
            "submit_public_inquiry(uuid, text, text, text, text, text, text, uuid)",
            "claim_outbox(text)",
            "finish_outbox(uuid, boolean)",
        ):
            connection.execute(text(f"ALTER FUNCTION perchpoint.{name} OWNER TO perchpoint_definer"))
    org_a, org_b = uuid4(), uuid4()
    actor_a, actor_b, expired = uuid4(), uuid4(), uuid4()
    params = {"org_a": org_a, "org_b": org_b, "actor_a": actor_a, "actor_b": actor_b, "expired": expired}
    statements = [
        "INSERT INTO organizations (id, name) VALUES (%(org_a)s, 'Bench Org A'), (%(org_b)s, 'Bench Org B')",
        """INSERT INTO accounts (id, email, password_hash) VALUES
          (%(actor_a)s, 'bench-a@example.com', 'bench'),
          (%(actor_b)s, 'bench-b@example.com', 'bench'),
          (%(expired)s, 'bench-expired@example.com', 'bench')""",
        """INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at, ended_at) VALUES
          (gen_random_uuid(), %(actor_a)s, %(org_a)s, 'leasing', '2020-01-01', NULL),
          (gen_random_uuid(), %(actor_b)s, %(org_b)s, 'leasing', '2020-01-01', NULL),
          (gen_random_uuid(), %(expired)s, %(org_a)s, 'leasing', '1999-01-01', '2001-01-01')""",
        """
        INSERT INTO properties (organization_id, id, name, property_type)
        SELECT CASE WHEN mod(g, 2) = 0 THEN %(org_a)s ELSE %(org_b)s END,
               gen_random_uuid(), 'Bench ' || g,
               CASE WHEN mod(g, 5) = 0 THEN 'mixed_use' ELSE 'multifamily' END
        FROM generate_series(1, 1000) AS g;
        """,
        """
        INSERT INTO buildings (organization_id, id, property_id, name, allowed_uses)
        SELECT p.organization_id, gen_random_uuid(), p.id, 'Bench building ' || p.name, ARRAY['residential','commercial']
        FROM properties p;
        """,
        """
        INSERT INTO spaces (organization_id, id, property_id, building_id, label, use, square_feet)
        SELECT b.organization_id, gen_random_uuid(), b.property_id, b.id,
               'Bench ' || b.name || ' ' || kind.n, kind.use, 700
        FROM buildings b
        CROSS JOIN (VALUES (1, 'residential'), (2, 'residential'), (3, 'commercial')) AS kind(n, use);
        """,
        """
        INSERT INTO space_states (
          organization_id, id, space_id, condition, occupancy, availability, publication,
          maintenance_restriction, legal_restriction, version, current)
        SELECT s.organization_id, gen_random_uuid(), s.id, 'rent_ready', 'vacant',
               CASE WHEN s.use = 'residential' THEN 'offerable' ELSE 'withheld' END,
               'unpublished', 'none', 'none', 1, true
        FROM spaces s;
        """,
        """
        INSERT INTO listings (
          organization_id, id, space_id, publication, availability, property_name, label, use,
          municipality, state, amount_minor, currency, version)
        SELECT s.organization_id, gen_random_uuid(), s.id,
               (ARRAY['published','unpublished','restricted'])[1 + mod(row_number() OVER (ORDER BY s.id)::int, 3)],
               'offerable', 'Bench listing', s.label, s.use, 'Cincinnati', 'OH', 120000, 'USD', 1
        FROM (
          SELECT DISTINCT ON (building_id) * FROM spaces WHERE use = 'residential' ORDER BY building_id, id
        ) s;
        """,
        """
        INSERT INTO inquiries (
          organization_id, id, listing_id, name, email, intent, message, status, version, received_at)
        SELECT l.organization_id, gen_random_uuid(), l.id, 'Bench guest ' || g, 'bench@example.com', 'showing',
               'benchmark', 'open', 1, now()
        FROM listings l CROSS JOIN generate_series(1, 25) AS g;
        """,
        """
        INSERT INTO households (organization_id, id, label)
        SELECT CASE WHEN mod(g, 2) = 0 THEN %(org_a)s ELSE %(org_b)s END,
               gen_random_uuid(), 'Bench person ' || g
        FROM generate_series(1, 5000) AS g;
        """,
        """
        INSERT INTO activity (organization_id, id, resource_type, resource_id, summary, occurred_at, actor_id)
        SELECT p.organization_id, gen_random_uuid(), 'record', p.id, 'bench', now(), %(actor_a)s
        FROM properties p CROSS JOIN generate_series(1, 250) AS g;
        """,
    ]
    with bench_admin.begin() as connection:
        for statement in statements:
            connection.exec_driver_sql(statement, params)
        counts = connection.execute(text("""
            SELECT
              (SELECT count(*) FROM properties),
              (SELECT count(*) FROM buildings),
              (SELECT count(*) FROM spaces),
              (SELECT count(*) FROM households),
              (SELECT count(*) FROM listings),
              (SELECT count(*) FROM inquiries),
              (SELECT count(*) FROM activity),
              (SELECT count(*) FROM organizations),
              (SELECT count(*) FROM memberships WHERE ended_at IS NULL),
              (SELECT count(*) FROM memberships WHERE ended_at IS NOT NULL)
        """)).one()
        sample_property = connection.execute(text("SELECT id FROM properties WHERE organization_id = :org LIMIT 1"), {"org": org_a}).scalar()
        sample_listing = connection.execute(text("SELECT id FROM listings WHERE organization_id = :org AND publication = 'published' LIMIT 1"), {"org": org_a}).scalar()
        sample_inquiry = connection.execute(text("SELECT id FROM inquiries WHERE organization_id = :org LIMIT 1"), {"org": org_a}).scalar()
        revision = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
    runtime = engine(settings.runtime_url.rsplit("/", 1)[0] + "/" + BENCH, pool_size=30, max_overflow=0)
    queries = {
        "property_list": "SELECT id, name FROM properties ORDER BY id LIMIT 50",
        "property_hierarchy": "SELECT b.id, s.id FROM buildings b JOIN spaces s ON s.building_id = b.id WHERE b.property_id = '%s'" % sample_property,
        "inquiry_queue": "SELECT id, status FROM inquiries ORDER BY received_at DESC LIMIT 50",
        "inquiry_detail": "SELECT id, status, message FROM inquiries WHERE id = '%s'" % sample_inquiry,
        "activity_timeline": "SELECT id, summary FROM activity WHERE resource_id = '%s' ORDER BY occurred_at DESC LIMIT 50" % sample_property,
        "public_listings": "SELECT listing_id FROM perchpoint.published_listings() WHERE property_name = 'Bench listing'",
        "public_listing_detail": "SELECT listing_id, label FROM perchpoint.published_listings() WHERE listing_id = '%s'" % sample_listing,
        "rls_other_org": "SELECT count(*) FROM properties",
    }
    print("server_version", version)
    print("revision", revision)
    print("runtime_role perchpoint_runtime")
    print("counts", tuple(counts))
    print("warmup 1 measured 10 query_count 10 plus one context statement each")
    try:
        with runtime.connect() as connection:
            for name, sql in queries.items():
                org = org_b if name == "rls_other_org" else org_a
                actor = actor_b if name == "rls_other_org" else actor_a
                p50, p95, maximum = measure(connection, org, actor, sql)
                print(f"{name} p50_ms {p50:.2f} p95_ms {p95:.2f} max_ms {maximum:.2f}")
                for line in explain(connection, org, actor, sql):
                    if "Scan" in line or "Index" in line or "Execution Time" in line:
                        print(f"plan {name}: {line.strip()}")
            hidden = connection.begin()
            connection.execute(
                text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true), set_config('app.request_id', :request, true)"),
                {"actor": str(actor_a), "org": str(org_a), "request": str(uuid4())},
            )
            visible = connection.execute(text("SELECT count(*) FROM properties")).scalar()
            hidden.rollback()
            print("rls_visible_org_a", visible)
        for label, sql in (
            ("concurrent_public_25", queries["public_listings"]),
            ("concurrent_internal_25", queries["property_list"]),
        ):
            p50, p95, maximum, _warmup = concurrent(runtime, org_a, actor_a, sql, 25)
            print(f"{label} p50_ms {p50:.2f} p95_ms {p95:.2f} max_ms {maximum:.2f}")
    finally:
        runtime.dispose()
        bench_admin.dispose()
        admin = engine(root + "/postgres")
        with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            connection.execute(text(f"DROP DATABASE IF EXISTS {BENCH} WITH (FORCE)"))
            gone = connection.execute(text("SELECT count(*) FROM pg_database WHERE datname = :name"), {"name": BENCH}).scalar()
        admin.dispose()
        development = engine_for(root + "/perchpoint_phase2")
        with development.connect() as connection:
            leftover = connection.execute(text("SELECT count(*) FROM properties WHERE name LIKE ('Bench ' || chr(37))")).scalar()
            elm = connection.execute(text("SELECT count(*) FROM properties WHERE id = :id"), {"id": sid("property-elm")}).scalar()
            head = connection.execute(text("SELECT version_num FROM alembic_version")).scalar()
        development.dispose()
        print("bench_database_remaining", gone)
        print("development_bench_properties", leftover)
        print("development_elm", elm)
        print("development_head", head)


if __name__ == "__main__":
    main()

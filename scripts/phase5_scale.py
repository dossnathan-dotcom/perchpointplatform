"""Load a disposable Phase 5 scale database and remove it."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from perchpoint.db import engine_for  # noqa: E402
from perchpoint.settings import Settings  # noqa: E402

DATABASE = "perchpoint_phase5_scale"


def main() -> None:
    settings = Settings.load()
    admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/postgres")
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": DATABASE})
        connection.execute(text(f"DROP DATABASE IF EXISTS {DATABASE}"))
        connection.execute(text(f"CREATE DATABASE {DATABASE}"))
        connection.execute(text(f"GRANT CONNECT, CREATE ON DATABASE {DATABASE} TO perchpoint_migrator"))
    admin.dispose()
    prepared = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + DATABASE)
    with prepared.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("GRANT ALL ON SCHEMA public TO perchpoint_migrator"))
        connection.execute(text("GRANT perchpoint_definer TO perchpoint_migrator"))
    prepared.dispose()
    migrator = os.environ["PHASE2_MIGRATOR_URL"]
    os.environ["PHASE2_MIGRATOR_URL"] = migrator.rsplit("/", 1)[0] + "/" + DATABASE
    subprocess.run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=BACKEND, check=True)
    os.environ["PHASE2_MIGRATOR_URL"] = migrator
    owned = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + DATABASE)
    with owned.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        for name in (
            "actor_in_org(uuid)",
            "published_listings()",
            "login_material(text)",
            "current_membership(uuid)",
            "submit_public_inquiry(uuid, text, text, text, text, text, text, uuid)",
            "claim_outbox(text)",
            "finish_outbox(uuid, boolean)",
            "accept_inbox(uuid, text, text, text, text, jsonb, integer)",
            "public_search(text)",
            "claim_document_job(text)",
        ):
            connection.execute(text(f"ALTER FUNCTION perchpoint.{name} OWNER TO perchpoint_definer"))
        connection.execute(text("GRANT USAGE ON SCHEMA perchpoint TO perchpoint_definer"))
        connection.execute(text("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA perchpoint TO perchpoint_definer"))
        connection.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO perchpoint_definer"))
    owned.dispose()
    scale = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + DATABASE)
    with scale.connect() as connection:
        connection.execute(text("INSERT INTO organizations (id, name, synthetic) VALUES (gen_random_uuid(), 'Scale Org', true)"))
        org = connection.execute(text("SELECT id FROM organizations LIMIT 1")).scalar()
        connection.execute(
            text(
                """
                INSERT INTO properties (organization_id, id, name, property_type)
                SELECT :org, gen_random_uuid(), 'Scale ' || n, 'single_family'
                FROM generate_series(1, 1000) AS n
                """
            ),
            {"org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO parties (organization_id, id, party_kind, display_name)
                SELECT :org, gen_random_uuid(), CASE WHEN n <= 1000 THEN 'household' ELSE 'person' END, 'Person ' || n
                FROM generate_series(1, 5000) AS n
                """
            ),
            {"org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO buildings (organization_id, id, property_id, name, allowed_uses)
                SELECT organization_id, gen_random_uuid(), id, 'Main', ARRAY['residential']
                FROM properties
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO spaces (organization_id, id, property_id, building_id, label, use, square_feet)
                SELECT b.organization_id, gen_random_uuid(), b.property_id, b.id, 'Space ' || n, 'residential', 800
                FROM buildings b
                CROSS JOIN generate_series(1, 3) AS n
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO documents (
                  organization_id, id, document_class, title, classification,
                  primary_resource_type, primary_resource_id, lifecycle
                )
                SELECT :org, gen_random_uuid(), 'internal-administration', 'Document ' || n, 'internal',
                  'organization', :org, 'available'
                FROM generate_series(1, 25000) AS n
                """
            ),
            {"org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO audit_events (
                  organization_id, id, actor_id, action, resource_type, resource_id, occurred_at,
                  correlation_id, result, event_hash
                )
                SELECT :org, gen_random_uuid(), NULL, 'scale.recorded', 'record', gen_random_uuid(), now(),
                  gen_random_uuid(), 'allowed', md5(n::text)
                FROM generate_series(1, 250000) AS n
                """
            ),
            {"org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO search_documents (
                  organization_id, id, resource_type, resource_id, title, body, classification
                )
                SELECT organization_id, gen_random_uuid(), 'property', id, name, property_type, 'internal'
                FROM properties
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO search_documents (
                  organization_id, id, resource_type, resource_id, title, body, classification
                )
                SELECT organization_id, gen_random_uuid(), 'document', id, title, 'synthetic body', classification
                FROM documents
                """
            )
        )
        other = connection.execute(text("SELECT gen_random_uuid()")).scalar()
        actor = connection.execute(text("SELECT gen_random_uuid()")).scalar()
        connection.execute(text("INSERT INTO organizations (id, name, synthetic) VALUES (:id, 'Scale Org B', true)"), {"id": other})
        connection.execute(
            text("INSERT INTO accounts (id, email, password_hash) VALUES (:id, :email, 'synthetic')"),
            {"id": actor, "email": f"scale-{actor}@example.com"},
        )
        connection.execute(
            text(
                """
                INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at)
                VALUES (gen_random_uuid(), :actor, :org, 'leasing', now())
                """
            ),
            {"actor": actor, "org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO search_documents (
                  organization_id, id, resource_type, resource_id, title, body, classification
                ) VALUES (:org, gen_random_uuid(), 'property', gen_random_uuid(), 'Hawthorn Lane 18', 'address', 'internal')
                """
            ),
            {"org": org},
        )
        connection.execute(text("ANALYZE search_documents"))
        connection.execute(text("GRANT CONNECT ON DATABASE perchpoint_phase5_scale TO perchpoint_runtime"))
        counts = connection.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM properties),
                  (SELECT count(*) FROM spaces),
                  (SELECT count(*) FROM parties),
                  (SELECT count(*) FROM documents),
                  (SELECT count(*) FROM audit_events)
                """
            )
        ).one()
        connection.commit()
    scale.dispose()
    runtime = engine_for(settings.runtime_url.rsplit("/", 1)[0] + "/" + DATABASE)
    samples = {name: [] for name in ("exact", "prefix", "phrase", "fuzzy", "facet")}
    with runtime.connect() as connection:
        connection.execute(
            text("SELECT set_config('app.actor_id', :actor, false), set_config('app.organization_id', :org, false), set_config('app.request_id', :request, false)"),
            {"actor": str(actor), "org": str(org), "request": str(actor)},
        )
        connection.execute(text("SET random_page_cost = 1.1"))
        connection.execute(text("SET cpu_tuple_cost = 0.05"))
        statements = {
            "exact": "SELECT count(*) FROM search_documents WHERE title = 'Scale 1'",
            "prefix": "SELECT count(*) FROM search_documents WHERE lower(title) LIKE 'scale %'",
            "phrase": "SELECT count(*) FROM search_documents WHERE search_vector @@ websearch_to_tsquery('simple', '\"Scale 1\"')",
            "fuzzy": "SELECT count(*) FROM search_documents WHERE title ILIKE '%Hawthorn%'",
            "facet": "SELECT resource_type, count(*) FROM search_documents GROUP BY resource_type",
        }
        for _ in range(5):
            for name, statement in statements.items():
                connection.execute(text(statement)).all()
        import time

        for _ in range(20):
            for name, statement in statements.items():
                started = time.perf_counter()
                connection.execute(text(statement)).all()
                samples[name].append((time.perf_counter() - started) * 1000)
        plan = connection.execute(text("EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM search_documents WHERE title = 'Scale 1'")).scalars().all()
        fuzzy_plan = connection.execute(text("EXPLAIN (ANALYZE, BUFFERS) SELECT count(*) FROM search_documents WHERE title ILIKE '%Hawthorn%'")).scalars().all()
        hidden = connection.execute(text("SELECT count(*) FROM search_documents WHERE title = 'Scale Org B'")).scalar()
        started = time.perf_counter()
        connection.execute(
            text(
                """
                INSERT INTO search_documents (organization_id, id, resource_type, resource_id, title, body, classification)
                VALUES (:org, gen_random_uuid(), 'property', gen_random_uuid(), 'Index Lag Probe', 'accepted', 'internal')
                """
            ),
            {"org": org},
        )
        connection.execute(text("SELECT count(*) FROM search_documents WHERE title = 'Index Lag Probe'")).scalar()
        lag_ms = (time.perf_counter() - started) * 1000
        connection.commit()
    runtime.dispose()
    for name, values in samples.items():
        values.sort()
        print(f"runtime_{name}_ms p50={values[len(values)//2]:.2f} p95={values[int(len(values)*0.95)-1]:.2f} max={values[-1]:.2f}")
    print("runtime_explain")
    print("\n".join(plan))
    print("runtime_fuzzy_explain")
    print("\n".join(fuzzy_plan))
    print(f"cross_org_visible={hidden} index_lag_ms={lag_ms:.2f}")
    print(
        f"properties={counts[0]} spaces={counts[1]} parties={counts[2]} documents={counts[3]} audit_events={counts[4]}"
    )
    cleanup = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/postgres")
    with cleanup.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": DATABASE})
        connection.execute(text(f"DROP DATABASE IF EXISTS {DATABASE}"))
    cleanup.dispose()
    print("scale database dropped")


if __name__ == "__main__":
    main()

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
            "search_rows(text, text, text, text)",
            "search_facets(text, text, text, text)",
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
        connection.execute(text("UPDATE search_documents SET body = 'ocr boilerplate token' WHERE title = 'Document 1'"))
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
    from dataclasses import replace
    from uuid import uuid4
    import time

    from perchpoint.phase5 import create_party, search_records

    scale_settings = replace(settings, runtime_url=settings.runtime_url.rsplit("/", 1)[0] + "/" + DATABASE)
    queries = {
        "exact": "Hawthorn Lane 18",
        "prefix": "Hawthorn",
        "phrase": '"Hawthorn Lane"',
        "fuzzy": "Hawth",
        "party": "Person 5000",
        "document": "Document 25000",
        "body": "boilerplate",
        "broad": "Scale",
    }
    samples = {name: [] for name in queries}
    for _ in range(5):
        for query in queries.values():
            search_records(scale_settings, actor, org, query)
    for _ in range(20):
        for name, query in queries.items():
            started = time.perf_counter()
            search_records(scale_settings, actor, org, query)
            samples[name].append((time.perf_counter() - started) * 1000)
    runtime = engine_for(scale_settings.runtime_url)
    with runtime.connect() as connection:
        connection.execute(
            text("SELECT set_config('app.actor_id', :actor, false), set_config('app.organization_id', :org, false), set_config('app.request_id', :request, false)"),
            {"actor": str(actor), "org": str(org), "request": str(actor)},
        )
        version = connection.execute(text("SHOW server_version")).scalar()
        plan = connection.execute(text("EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM perchpoint.search_rows('Hawth', 'Hawth', 'Hawth%', '%Hawth%')")).scalars().all()
        phrase_plan = connection.execute(text("EXPLAIN (ANALYZE, BUFFERS) SELECT * FROM perchpoint.search_rows('\"Hawthorn Lane\"', 'Hawthorn Lane', 'Hawthorn%', '%Hawthorn%')")).scalars().all()
        hidden = connection.execute(text("SELECT count(*) FROM search_documents WHERE title = 'Scale Org B'")).scalar()
        connection.rollback()
    runtime.dispose()
    lags = []
    for index in range(20):
        label = f"Lag Probe {index:02d}"
        started = time.perf_counter()
        create_party(scale_settings, actor, org, {"party_kind": "person", "display_name": label}, f"lag-{index}-{actor}", uuid4())
        visible = search_records(scale_settings, actor, org, label)
        lags.append((time.perf_counter() - started) * 1000)
        if not any(item["title"] == label for item in visible["results"]):
            raise SystemExit(f"index lag missed {label}")
    lags.sort()
    print(f"postgres={version} warmup=5 samples=20 connections=1")
    for name, values in samples.items():
        values.sort()
        print(f"runtime_{name}_ms p50={values[len(values)//2]:.2f} p95={values[int(len(values)*0.95)-1]:.2f} max={values[-1]:.2f}")
    print("runtime_fuzzy_explain")
    print("\n".join(plan))
    print("runtime_phrase_explain")
    print("\n".join(phrase_plan))
    print(f"cross_org_visible={hidden}")
    print(f"index_lag_ms p50={lags[len(lags)//2]:.2f} p95={lags[int(len(lags)*0.95)-1]:.2f} max={lags[-1]:.2f}")
    print(
        f"properties={counts[0]} spaces={counts[1]} parties={counts[2]} documents={counts[3]} audit_events={counts[4]}"
    )
    cleanup = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/postgres")
    with cleanup.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": DATABASE})
        connection.execute(text(f"DROP DATABASE IF EXISTS {DATABASE}"))
    cleanup.dispose()
    print("scale database dropped")
    for name, values in samples.items():
        if name in {"exact", "prefix", "phrase", "fuzzy", "party", "document", "body", "broad"} and values[int(len(values) * 0.95) - 1] >= 300:
            raise SystemExit(f"{name} p95 {values[int(len(values) * 0.95) - 1]:.2f} exceeds 300 ms")
    if lags[-1] >= 5000:
        raise SystemExit("indexing lag exceeded five seconds")


if __name__ == "__main__":
    runs = int(os.environ.get("PHASE5_SCALE_RUNS", "3"))
    for run in range(1, runs + 1):
        print(f"scale_run={run}")
        main()

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
                SELECT :org, gen_random_uuid(), 'person', 'Person ' || n
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
        import time

        samples = []
        for _ in range(20):
            started = time.perf_counter()
            connection.execute(text("SELECT count(*) FROM search_documents WHERE title = 'Scale 1'")).scalar()
            samples.append((time.perf_counter() - started) * 1000)
        samples.sort()
        print(f"search_exact_ms p50={samples[len(samples)//2]:.2f} p95={samples[int(len(samples)*0.95)-1]:.2f} max={samples[-1]:.2f}")
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

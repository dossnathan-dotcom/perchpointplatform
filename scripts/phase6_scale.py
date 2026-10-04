"""Disposable Phase 6 authorization benchmark. Drops its database afterward."""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

from sqlalchemy import text

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
sys.path.insert(0, str(BACKEND))

from perchpoint.db import engine_for  # noqa: E402
from perchpoint.settings import Settings  # noqa: E402

DATABASE = "perchpoint_phase6_scale"


def _percentile(values: list[float], fraction: float) -> float:
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(len(ordered) * fraction) - 1))
    return ordered[index]


def _prepare(settings: Settings) -> tuple[str, str]:
    admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/postgres")
    with admin.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": DATABASE})
        connection.execute(text(f"DROP DATABASE IF EXISTS {DATABASE}"))
        connection.execute(text(f"CREATE DATABASE {DATABASE}"))
        connection.execute(text(f"GRANT CONNECT, CREATE ON DATABASE {DATABASE} TO perchpoint_migrator, perchpoint_runtime"))
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
            "current_membership(uuid)",
            "resolve_session(text)",
            "record_provider_session(uuid, text, uuid, text, text, text, text, timestamp with time zone, timestamp with time zone, integer, text, text)",
            "search_rows(text, text, text, text)",
        ):
            connection.execute(text(f"ALTER FUNCTION perchpoint.{name} OWNER TO perchpoint_definer"))
        connection.execute(text("GRANT USAGE ON SCHEMA perchpoint TO perchpoint_runtime, perchpoint_definer"))
        connection.execute(text("GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA perchpoint TO perchpoint_runtime, perchpoint_definer"))
        connection.execute(text("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO perchpoint_runtime, perchpoint_definer"))
    owned.dispose()
    scale = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + DATABASE)
    with scale.begin() as connection:
        org = connection.execute(text("INSERT INTO organizations (id, name, synthetic) VALUES (gen_random_uuid(), 'Scale Org', true) RETURNING id")).scalar()
        other = connection.execute(text("INSERT INTO organizations (id, name, synthetic) VALUES (gen_random_uuid(), 'Scale Org B', true) RETURNING id")).scalar()
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
            text("INSERT INTO properties (organization_id, id, name, property_type) VALUES (:org, gen_random_uuid(), 'Hidden property', 'single_family')"),
            {"org": other},
        )
        connection.execute(
            text(
                """
                INSERT INTO buildings (organization_id, id, property_id, name, allowed_uses)
                SELECT organization_id, gen_random_uuid(), id, 'Main', ARRAY['residential'] FROM properties WHERE organization_id = :org
                """
            ),
            {"org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO spaces (organization_id, id, property_id, building_id, label, use, square_feet)
                SELECT b.organization_id, gen_random_uuid(), b.property_id, b.id, 'Space ' || n, 'residential', 800
                FROM buildings b CROSS JOIN generate_series(1, 3) AS n
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO parties (organization_id, id, party_kind, display_name)
                SELECT :org, gen_random_uuid(), 'person', 'Person ' || n FROM generate_series(1, 5000) AS n
                """
            ),
            {"org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO accounts (id, email, password_hash)
                SELECT gen_random_uuid(), 'scale-' || n || '@example.com', 'provider-owned'
                FROM generate_series(1, 5000) AS n
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO identity_accounts (id, account_id, provider_subject, status, email_verified, assurance)
                SELECT gen_random_uuid(), id, 'scale:' || id::text, 'active', true, 'aal1' FROM accounts
                """
            )
        )
        connection.execute(
            text(
                """
                INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at)
                SELECT gen_random_uuid(), id, :org, 'leasing', now() FROM accounts
                """
            ),
            {"org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO documents (
                  organization_id, id, document_class, title, classification, primary_resource_type, primary_resource_id, lifecycle
                )
                SELECT :org, gen_random_uuid(), 'internal-administration', 'Document ' || n, 'internal', 'organization', :org, 'available'
                FROM generate_series(1, 25000) AS n
                """
            ),
            {"org": org},
        )
        connection.execute(
            text(
                """
                INSERT INTO audit_events (
                  organization_id, id, actor_id, action, resource_type, resource_id, occurred_at, correlation_id, result, event_hash
                )
                SELECT :org, gen_random_uuid(), NULL, 'scale.recorded', 'record', gen_random_uuid(), now(), gen_random_uuid(), 'allowed', md5(n::text)
                FROM generate_series(1, 250000) AS n
                """
            ),
            {"org": org},
        )
        actor = connection.execute(text("SELECT id FROM accounts ORDER BY email LIMIT 1")).scalar()
        token_hash = "scale-session"
        connection.execute(
            text(
                """
                SELECT perchpoint.record_provider_session(
                  :account, :subject, :org, :token_hash, :csrf, 'aal1', 'benchmark',
                  now() + interval '1 hour', now() + interval '8 hours', 3600, 'provider-session', NULL
                )
                """
            ),
            {"account": actor, "subject": f"scale:{actor}", "org": org, "token_hash": token_hash, "csrf": "csrf"},
        )
        counts = connection.execute(
            text(
                """
                SELECT
                  (SELECT count(*) FROM properties),
                  (SELECT count(*) FROM spaces),
                  (SELECT count(*) FROM parties),
                  (SELECT count(*) FROM identity_accounts),
                  (SELECT count(*) FROM memberships WHERE ended_at IS NULL),
                  (SELECT count(*) FROM documents),
                  (SELECT count(*) FROM audit_events)
                """
            )
        ).one()
    scale.dispose()
    return str(actor), str(org), token_hash, counts


def _measure(settings: Settings, actor: str, organization: str, token_hash: str) -> dict[str, list[float]]:
    runtime = engine_for(settings.runtime_url.rsplit("/", 1)[0] + "/" + DATABASE)
    samples = {"session": [], "decision": [], "property_list": [], "cross_org": []}
    with runtime.connect() as connection:
        for _ in range(5):
            connection.execute(text("SELECT * FROM perchpoint.resolve_session(:token)"), {"token": token_hash})
            connection.execute(text("SELECT * FROM perchpoint.current_membership(:actor)"), {"actor": actor})
        for _ in range(20):
            started = time.perf_counter()
            connection.execute(text("SELECT account_id FROM perchpoint.resolve_session(:token)"), {"token": token_hash})
            samples["session"].append((time.perf_counter() - started) * 1000)
            started = time.perf_counter()
            connection.execute(text("SELECT role_name FROM perchpoint.current_membership(:actor)"), {"actor": actor})
            samples["decision"].append((time.perf_counter() - started) * 1000)
            started = time.perf_counter()
            connection.execute(
                text("SELECT set_config('app.actor_id', :actor, true), set_config('app.organization_id', :org, true)"),
                {"actor": actor, "org": organization},
            )
            connection.execute(text("SELECT count(*) FROM properties"))
            samples["property_list"].append((time.perf_counter() - started) * 1000)
            hidden = connection.execute(text("SELECT count(*) FROM properties WHERE name = 'Hidden property'")).scalar()
            samples["cross_org"].append(float(hidden or 0))
        connection.rollback()
    runtime.dispose()
    return samples


def _drop(settings: Settings) -> None:
    cleanup = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/postgres")
    with cleanup.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
        connection.execute(text("SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = :name AND pid <> pg_backend_pid()"), {"name": DATABASE})
        connection.execute(text(f"DROP DATABASE IF EXISTS {DATABASE}"))
    cleanup.dispose()


def main() -> None:
    settings = Settings.load()
    rounds = int(os.environ.get("PHASE6_SCALE_RUNS", "3"))
    failures = []
    lines = []
    for index in range(1, rounds + 1):
        actor, organization, token_hash, counts = _prepare(settings)
        samples = _measure(settings, actor, organization, token_hash)
        session_p95 = _percentile(samples["session"], 0.95)
        decision_p95 = _percentile(samples["decision"], 0.95)
        list_p95 = _percentile(samples["property_list"], 0.95)
        hidden = max(samples["cross_org"])
        line = (
            f"round={index} properties={counts[0]} spaces={counts[1]} parties={counts[2]} identities={counts[3]} "
            f"memberships={counts[4]} documents={counts[5]} audit={counts[6]} "
            f"session_p95={session_p95:.2f} decision_p95={decision_p95:.2f} list_p95={list_p95:.2f} cross_org={hidden:.0f}"
        )
        print(line)
        lines.append(line)
        _drop(settings)
        if session_p95 >= 100 or decision_p95 >= 50 or list_p95 >= 300 or hidden != 0 or counts[0] < 1000 or counts[6] < 250000:
            failures.append(index)
    report = ROOT / "test_reports" / "phase6"
    report.mkdir(parents=True, exist_ok=True)
    (report / "scale.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")
    if failures:
        raise SystemExit(f"benchmark rounds failed: {failures}")
    print("phase6_scale=passed")


if __name__ == "__main__":
    main()

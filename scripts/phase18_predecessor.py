"""Upgrade a disposable database from the accepted Phase 17 head to Phase 18.

Port 54342 stays clear of the presentation database on 54339 and the Phase 17
predecessor on 54340. Phase 17's own script still stops at 0060.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "postgres:16@sha256:1a6ab3f5345eb6dbe04a1349529caabdb0ab09293a09590fad07b2246bfa4b54"
CONTAINER = "perchpoint-phase18-predecessor"
PASSWORD = "local-only-not-production"
PORT = "54342"
ADMIN = f"postgresql+psycopg://postgres:{PASSWORD}@127.0.0.1:{PORT}/postgres"
MIGRATOR = f"postgresql+psycopg://perchpoint_migrator:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"
PREDECESSOR = "0060_phase17_grant_accept"
HEAD = "0064_phase18_return_completion"
ORG = "11111111-1111-4111-8111-111111111111"
OBLIGATION = "22222222-2222-4222-8222-222222222222"
GRANT = "33333333-3333-4333-8333-333333333333"
ORDER = "44444444-4444-4444-8444-444444444444"


def _run(command: list[str], *, cwd: Path = ROOT, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if check and completed.returncode:
        raise RuntimeError(f"{command} failed\n{completed.stdout}\n{completed.stderr}")
    return completed


def _psql(sql: str, database: str = "postgres") -> str:
    completed = _run(
        [
            "docker", "exec", CONTAINER, "psql", "-v", "ON_ERROR_STOP=1",
            "-U", "postgres", "-d", database, "-At", "-c", sql,
        ]
    )
    return completed.stdout.strip()


def _wait_ready() -> None:
    deadline = time.time() + 60
    while time.time() < deadline:
        probe = _run(["docker", "exec", CONTAINER, "pg_isready", "-U", "postgres"], check=False)
        if probe.returncode == 0:
            print(f"ready {CONTAINER}")
            return
        time.sleep(1)
    raise RuntimeError(f"{CONTAINER} did not become ready")


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PHASE2_ADMIN_URL": ADMIN,
            "PHASE2_MIGRATOR_URL": MIGRATOR,
            "PHASE2_RUNTIME_URL": MIGRATOR.replace("perchpoint_migrator", "perchpoint_runtime"),
            "PHASE2_JWT_SECRET": "local-only-not-production-jwt-secret-32-plus",
            "PHASE2_DEV_PASSWORD": PASSWORD + "-password",
            "PHASE2_WEBHOOK_SECRET": PASSWORD + "-webhook",
            "PHASE3_ENVIRONMENT": "local",
            "PHASE6_ALLOW_DEV_JWT": "1",
            "PHASE6_AUTH_URL": "http://127.0.0.1:9998",
            "PHASE6_PROVIDER_JWT_SECRET": "local-only-not-production-gotrue-jwt-secret",
            "PHASE6_ALLOWED_ORIGINS": "http://127.0.0.1:3000,http://localhost:3000,http://testserver",
            "PYTHONPATH": str(ROOT / "backend"),
        }
    )
    return env


def _forced(database: str = "perchpoint_phase2") -> str:
    return _psql(
        "SELECT count(*) FILTER (WHERE c.relforcerowsecurity) || '/' || count(*) "
        "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
        "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity",
        database,
    )


def main() -> int:
    if "--execute" not in sys.argv:
        print("refusing to run without --execute")
        return 1
    _run(["docker", "rm", "-f", CONTAINER], check=False)
    try:
        _run(
            [
                "docker", "run", "-d", "--name", CONTAINER,
                "-p", f"127.0.0.1:{PORT}:5432",
                "-e", "POSTGRES_USER=postgres",
                "-e", f"POSTGRES_PASSWORD={PASSWORD}",
                "-e", "POSTGRES_DB=postgres",
                IMAGE,
            ]
        )
        _wait_ready()
        for statement in (
            "CREATE ROLE perchpoint_migrator LOGIN NOBYPASSRLS NOSUPERUSER PASSWORD 'local-only-not-production'",
            "CREATE ROLE perchpoint_runtime LOGIN NOBYPASSRLS NOSUPERUSER PASSWORD 'local-only-not-production'",
            "CREATE ROLE perchpoint_definer NOLOGIN BYPASSRLS NOSUPERUSER",
            "CREATE DATABASE perchpoint_phase2",
        ):
            _psql(statement)
        _psql("GRANT CONNECT, CREATE ON DATABASE perchpoint_phase2 TO perchpoint_migrator")
        _psql("GRANT CONNECT ON DATABASE perchpoint_phase2 TO perchpoint_runtime")
        _psql("GRANT ALL ON SCHEMA public TO perchpoint_migrator", "perchpoint_phase2")
        _psql("GRANT perchpoint_definer TO perchpoint_migrator", "perchpoint_phase2")
        env = _env()
        _run([sys.executable, "-m", "alembic", "upgrade", PREDECESSOR], cwd=ROOT / "backend", env=env)
        version = _psql("SELECT version_num FROM alembic_version", "perchpoint_phase2")
        if version != PREDECESSOR:
            raise RuntimeError(f"predecessor head was {version}")
        if _psql("SELECT to_regclass('public.digital_receipts')", "perchpoint_phase2") not in {"", "None"}:
            raise RuntimeError("Phase 18 receipts existed at the Phase 17 head")
        _psql(
            "INSERT INTO organizations (id, name, synthetic) VALUES "
            f"('{ORG}', 'Phase 18 upgrade household', true)",
            "perchpoint_phase2",
        )
        _psql(
            "INSERT INTO payment_obligations "
            "(organization_id, id, public_reference, tenancy_code, category, description, amount_minor, state, currency_code) "
            f"VALUES ('{ORG}', '{OBLIGATION}', 'p18-upgrade-obligation', 'tenancy-upgrade', 'rent', "
            "'Preserved resident rent', 40000, 'published', 'USD')",
            "perchpoint_phase2",
        )
        _psql(
            "INSERT INTO payer_grants "
            "(organization_id, id, tenancy_code, grantor_account_id, email, state) "
            f"VALUES ('{ORG}', '{GRANT}', 'tenancy-upgrade', '{ORG}', 'payer.upgrade@example.com', 'invited')",
            "perchpoint_phase2",
        )
        _psql(
            "INSERT INTO payment_orders "
            "(organization_id, id, public_reference, obligation_id, tenancy_code, payer_account_id, amount_minor, "
            "fee_minor, method, state, environment, idempotency_key, ledger_status) "
            f"VALUES ('{ORG}', '{ORDER}', 'p18-upgrade-order', '{OBLIGATION}', 'tenancy-upgrade', '{ORG}', "
            "40000, 0, 'card', 'succeeded', 'local_fake', 'p18-upgrade-order', 'posted')",
            "perchpoint_phase2",
        )
        before = _forced()
        print(f"predecessor={version} forced_rls={before}")
        _run([sys.executable, "-m", "alembic", "upgrade", HEAD], cwd=ROOT / "backend", env=env)
        version = _psql("SELECT version_num FROM alembic_version", "perchpoint_phase2")
        preserved = _psql(
            "SELECT obligation.amount_minor::text || ',' || payment.state || ',' || grant_row.state "
            "FROM payment_obligations obligation "
            "JOIN payment_orders payment ON payment.obligation_id = obligation.id "
            "JOIN payer_grants grant_row ON grant_row.tenancy_code = obligation.tenancy_code "
            f"WHERE obligation.id = '{OBLIGATION}'",
            "perchpoint_phase2",
        )
        receipts = _psql("SELECT to_regclass('public.digital_receipts')", "perchpoint_phase2")
        label = _psql(
            "SELECT column_name FROM information_schema.columns "
            "WHERE table_name = 'assistance_determinations' AND column_name = 'household_label'",
            "perchpoint_phase2",
        )
        role = _psql("SELECT rolsuper::text || ',' || rolbypassrls::text FROM pg_roles WHERE rolname = 'perchpoint_runtime'")
        after = _forced()
        print(f"migration_head={version} preserved={preserved} receipts={receipts} household_label={label} runtime={role} forced_rls={after}")
        if version != HEAD or preserved != "40000,succeeded,invited" or receipts != "digital_receipts":
            raise RuntimeError("predecessor upgrade did not preserve Phase 17 money or reach Phase 18")
        if label != "household_label" or role != "false,false":
            raise RuntimeError("Phase 18 head is missing its return column or the runtime role")
        if before == after:
            raise RuntimeError("Phase 18 tables did not change the forced row-security count")
        print("predecessor_upgrade=passed")
        return 0
    finally:
        _run(["docker", "rm", "-f", CONTAINER], check=False)


if __name__ == "__main__":
    raise SystemExit(main())

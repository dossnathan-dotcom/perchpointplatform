"""Representative Phase 18 assistance scale on a disposable database.

The presentation database on port 54339 is not cloned and is not written.
Thresholds are printed before any timed query. Database timing only.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import uuid4

from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "postgres:16@sha256:1a6ab3f5345eb6dbe04a1349529caabdb0ab09293a09590fad07b2246bfa4b54"
CONTAINER = "perchpoint-phase18-bench"
PASSWORD = "local-only-not-production"
PORT = "54348"
HEAD = "0064_phase18_return_completion"
ADMIN = f"postgresql+psycopg://postgres:{PASSWORD}@127.0.0.1:{PORT}/postgres"
MIGRATOR = f"postgresql+psycopg://perchpoint_migrator:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"
RUNTIME = f"postgresql+psycopg://perchpoint_runtime:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"

CONNECTIONS = 25
ROUNDS = 3
READ_P95_MS = 300
DETERMINATIONS = 200
RECEIPTS = 1000
CLAIM_ATTEMPTS = 8


def _run(command: list[str], *, cwd: Path = ROOT, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if check and completed.returncode:
        raise RuntimeError(f"{command[0:4]} failed with exit {completed.returncode}\n{completed.stdout[-2000:]}\n{completed.stderr[-2000:]}")
    return completed


def _psql(sql: str, database: str = "postgres") -> str:
    completed = _run(
        ["docker", "exec", CONTAINER, "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database, "-At", "-c", sql]
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
    for name in (
        "PHASE2_ADMIN_URL",
        "PHASE2_MIGRATOR_URL",
        "PHASE2_RUNTIME_URL",
        "PHASE2_JWT_SECRET",
        "PHASE2_DEV_PASSWORD",
        "PHASE2_WEBHOOK_SECRET",
        "PHASE6_SESSION_KEY",
        "PHASE6_PROVIDER_JWT_SECRET",
        "PHASE6_AUTH_URL",
        "PERCHPOINT_ALEMBIC_TARGET",
    ):
        env.pop(name, None)
    env.update(
        {
            "PHASE2_ADMIN_URL": ADMIN,
            "PHASE2_MIGRATOR_URL": MIGRATOR,
            "PHASE2_RUNTIME_URL": RUNTIME,
            "PHASE2_JWT_SECRET": "local-only-not-production-jwt-secret-32-plus",
            "PHASE2_DEV_PASSWORD": PASSWORD + "-password",
            "PHASE2_WEBHOOK_SECRET": PASSWORD + "-webhook",
            "PHASE3_ENVIRONMENT": "local",
            "DEMO_MODE": "1",
            "PHASE6_ALLOW_DEV_JWT": "1",
            "PYTHONPATH": str(ROOT / "backend"),
        }
    )
    return env


def _declare() -> None:
    print("declared_before_measure")
    print(f"dataset determinations={DETERMINATIONS} receipts={RECEIPTS} claim_attempts={CLAIM_ATTEMPTS}")
    print(f"thresholds connections={CONNECTIONS} rounds={ROUNDS} read_p95_ms<{READ_P95_MS} one_claim=1")
    print("measured=database_only api=not_measured worker_process=not_measured browser=not_measured")


def _percentile(samples: list[float], fraction: float) -> float:
    ordered = sorted(samples)
    index = min(len(ordered) - 1, max(0, int(round(fraction * (len(ordered) - 1)))))
    return ordered[index]


def _scope(connection, organization, actor, membership) -> None:
    connection.execute(
        text(
            "SELECT set_config('app.organization_id', :organization, true), "
            "set_config('app.actor_id', :actor, true), "
            "set_config('app.membership_id', :membership, true)"
        ),
        {"organization": str(organization), "actor": str(actor), "membership": str(membership)},
    )


def _read_once(engine, organization, actor, membership, statement: str) -> float:
    started = time.perf_counter()
    with engine.connect() as connection:
        with connection.begin():
            connection.execute(text("SET LOCAL statement_timeout = '10s'"))
            _scope(connection, organization, actor, membership)
            connection.execute(text(statement)).scalar_one()
    return (time.perf_counter() - started) * 1000


def _load(admin, organization) -> str:
    with admin.begin() as connection:
        for index in range(DETERMINATIONS):
            connection.execute(
                text(
                    "INSERT INTO assistance_determinations "
                    "(organization_id, id, public_reference, tenancy_code, program_kind, agency_name, service_period, version, "
                    "rent_to_owner_minor, resident_minor, agency_minor, state) "
                    "VALUES (:org, gen_random_uuid(), :reference, :tenancy, 'hcv', 'Synthetic housing agency', '2026-11', 1, "
                    "150000, 40000, 110000, 'approved')"
                ),
                {"org": organization, "reference": f"bench-det-{index}", "tenancy": f"bench-tenancy-{index}"},
            )
        hot = str(uuid4())
        connection.execute(
            text(
                "INSERT INTO digital_receipts "
                "(organization_id, id, public_reference, source, economic_key, method, amount_minor, currency_code, "
                "tenancy_code, service_period, purpose, effect_class, state, application_state, environment, money_moved, real_values_activated) "
                "VALUES (:org, :id, :reference, 'business_bank', :key, 'bank_transfer', 40000, 'USD', "
                "'bench-tenancy-0', '2026-11', 'resident_rent', 'resident_settlement', 'confirmed', 'queued', 'local_fake', false, false)"
            ),
            {"org": organization, "id": hot, "reference": "bench-hot-receipt", "key": "bench-hot"},
        )
        for index in range(RECEIPTS):
            connection.execute(
                text(
                    "INSERT INTO digital_receipts "
                    "(organization_id, id, public_reference, source, economic_key, method, amount_minor, currency_code, "
                    "tenancy_code, service_period, purpose, effect_class, state, application_state, environment, money_moved, real_values_activated) "
                    "VALUES (:org, gen_random_uuid(), :reference, 'business_bank', :key, 'bank_transfer', 40000, 'USD', "
                    ":tenancy, '2026-11', 'resident_rent', 'resident_settlement', 'confirmed', 'queued', 'local_fake', false, false)"
                ),
                {
                    "org": organization,
                    "reference": f"bench-receipt-{index}",
                    "key": f"bench-receipt-{index}",
                    "tenancy": f"bench-tenancy-{index % DETERMINATIONS}",
                },
            )
    return hot


def _claim_once(engine, organization, actor, membership, receipt_id) -> int:
    with engine.connect() as connection:
        with connection.begin():
            _scope(connection, organization, actor, membership)
            row = connection.execute(
                text(
                    "UPDATE digital_receipts SET application_state = 'claimed' "
                    "WHERE id = :id AND application_state = 'queued' RETURNING id"
                ),
                {"id": receipt_id},
            ).first()
    return 1 if row is not None else 0


def main() -> int:
    if "--execute" not in sys.argv:
        print("refusing to run without --execute")
        return 1
    _declare()
    _run(["docker", "rm", "-f", CONTAINER], check=False)
    admin = None
    runtime = None
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
        env = _env()
        _run([sys.executable, "-m", "perchpoint.bootstrap"], cwd=ROOT / "backend", env=env)
        version = _psql("SELECT version_num FROM alembic_version", "perchpoint_phase2")
        print(f"migration_head={version}")
        if version != HEAD:
            raise RuntimeError(f"unexpected head {version}")
        _run([sys.executable, "-m", "perchpoint.seed"], cwd=ROOT / "backend", env=env)
        admin = create_engine(ADMIN.rsplit("/", 1)[0] + "/perchpoint_phase2")
        with admin.connect() as connection:
            organization = connection.execute(text("SELECT id FROM organizations WHERE name LIKE 'HawkVision%'")).scalar_one()
            actor = connection.execute(text("SELECT id FROM accounts WHERE email = 'ann.synthetic@example.com'")).scalar_one()
            membership = connection.execute(
                text(
                    "SELECT id FROM memberships WHERE account_id = :actor AND organization_id = :organization "
                    "AND role_name = 'operations_manager'"
                ),
                {"actor": actor, "organization": organization},
            ).scalar_one()
        hot = _load(admin, organization)
        print(f"loaded determinations={DETERMINATIONS} receipts={RECEIPTS + 1}")
        runtime = create_engine(RUNTIME, pool_size=CONNECTIONS, max_overflow=0)
        with runtime.connect() as connection:
            with connection.begin():
                _scope(connection, organization, actor, membership)
                visible = int(connection.execute(text("SELECT count(*) FROM digital_receipts WHERE application_state = 'queued'")).scalar_one())
        print(f"visible_queued_receipts={visible}")
        if visible != RECEIPTS + 1:
            raise RuntimeError(f"runtime role saw {visible} queued receipts")
        statements = {
            "queued_receipts": "SELECT count(*) FROM digital_receipts WHERE application_state = 'queued'",
            "approved_determinations": "SELECT count(*) FROM assistance_determinations WHERE state = 'approved'",
        }
        failed = False
        for name, statement in statements.items():
            samples = []
            errors = 0
            for _ in range(ROUNDS):
                with ThreadPoolExecutor(max_workers=CONNECTIONS) as pool:
                    futures = [pool.submit(_read_once, runtime, organization, actor, membership, statement) for _ in range(CONNECTIONS)]
                    for future in futures:
                        try:
                            samples.append(future.result())
                        except Exception as exc:
                            errors += 1
                            if errors == 1:
                                print(f"read_error {name} {type(exc).__name__}: {exc}")
            p95 = round(_percentile(samples, 0.95), 3) if samples else 0
            print(f"read {name} samples={len(samples)} p95_ms={p95} errors={errors}")
            if errors or p95 >= READ_P95_MS:
                failed = True
        with ThreadPoolExecutor(max_workers=CLAIM_ATTEMPTS) as pool:
            claims = list(pool.map(lambda _index: _claim_once(runtime, organization, actor, membership, hot), range(CLAIM_ATTEMPTS)))
        print(f"claims={sum(claims)} attempts={CLAIM_ATTEMPTS}")
        if sum(claims) != 1:
            failed = True
        print("phase18_benchmark=" + ("passed" if not failed else "failed"))
        return 1 if failed else 0
    finally:
        if runtime is not None:
            runtime.dispose()
        if admin is not None:
            admin.dispose()
        _run(["docker", "rm", "-f", CONTAINER], check=False)


if __name__ == "__main__":
    sys.exit(main())

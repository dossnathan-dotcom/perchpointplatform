"""Prove Phase 20 from an empty database, including an upgrade from 0065.

The container is removed afterward. It does not use port 5432 or 54339.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "postgres:16@sha256:1a6ab3f5345eb6dbe04a1349529caabdb0ab09293a09590fad07b2246bfa4b54"
CONTAINER = os.environ.get("PHASE20_CLEAN_ROOM_CONTAINER", "perchpoint-phase20-cleanroom")
PASSWORD = "local-only-not-production"
PORT = os.environ.get("PHASE20_CLEAN_ROOM_PORT", "54366")
HEAD = "0066_phase20_maintenance"
PRIOR = "0065_phase19_reconciliation"
ADMIN = f"postgresql+psycopg://postgres:{PASSWORD}@127.0.0.1:{PORT}/postgres"
MIGRATOR = f"postgresql+psycopg://perchpoint_migrator:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"
RUNTIME = f"postgresql+psycopg://perchpoint_runtime:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"


def _run(command: list[str], *, cwd: Path = ROOT, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if check and completed.returncode:
        raise RuntimeError(f"{command} failed\n{completed.stdout[-4000:]}\n{completed.stderr[-4000:]}")
    return completed


def _psql(sql: str, database: str = "postgres") -> str:
    completed = _run([
        "docker", "exec", CONTAINER, "psql", "-v", "ON_ERROR_STOP=1",
        "-U", "postgres", "-d", database, "-At", "-c", sql,
    ])
    return completed.stdout.strip()


def _wait_ready() -> None:
    deadline = time.time() + 60
    while time.time() < deadline:
        if _run(["docker", "exec", CONTAINER, "pg_isready", "-U", "postgres"], check=False).returncode == 0:
            print(f"ready {CONTAINER}")
            return
        time.sleep(1)
    raise RuntimeError(f"{CONTAINER} did not become ready")


def _env(target: str | None) -> dict[str, str]:
    env = os.environ.copy()
    for name in (
        "PHASE2_ADMIN_URL", "PHASE2_MIGRATOR_URL", "PHASE2_RUNTIME_URL", "PHASE2_JWT_SECRET",
        "PHASE2_DEV_PASSWORD", "PHASE2_WEBHOOK_SECRET", "PHASE6_SESSION_KEY", "PHASE6_PROVIDER_JWT_SECRET",
        "PHASE6_AUTH_URL", "PERCHPOINT_ALEMBIC_TARGET", "PERCHPOINT_LOCAL_DEMO_PASSWORD",
    ):
        env.pop(name, None)
    env.update({
        "PHASE2_ADMIN_URL": ADMIN,
        "PHASE2_MIGRATOR_URL": MIGRATOR,
        "PHASE2_RUNTIME_URL": RUNTIME,
        "PHASE2_JWT_SECRET": "local-only-not-production-jwt-secret-32-plus",
        "PHASE2_DEV_PASSWORD": PASSWORD + "-password",
        "PHASE2_WEBHOOK_SECRET": PASSWORD + "-webhook",
        "PHASE3_ENVIRONMENT": "local",
        "DEMO_MODE": "1",
        "PHASE6_ALLOW_DEV_JWT": "1",
        "PHASE6_ALLOWED_ORIGINS": "http://127.0.0.1:3000,http://localhost:3000,http://testserver",
        "PHASE6_AUTH_URL": "http://127.0.0.1:9998",
        "PHASE6_PROVIDER_JWT_SECRET": "local-only-not-production-gotrue-jwt-secret",
        "PYTHONPATH": str(ROOT / "backend"),
    })
    if target:
        env["PERCHPOINT_ALEMBIC_TARGET"] = target
    return env


def _scale() -> None:
    print("thresholds cases=200 events=200 needs=200 time_rows=200 concurrent_timer_starts=2 read_p95_ms<300")
    organization = _psql("SELECT id FROM organizations LIMIT 1", "perchpoint_phase2")
    actor = _psql("SELECT id FROM accounts LIMIT 1", "perchpoint_phase2")
    if not organization or not actor:
        raise RuntimeError("scale needs a seeded organization and account")
    for start in range(0, 200, 20):
        case_rows = []
        event_rows = []
        need_rows = []
        time_rows = []
        report_rows = []
        for index in range(start, start + 20):
            case_id = str(uuid4())
            case_rows.append(f"('{organization}', '{case_id}', 'open', '{actor}')")
            event_rows.append(f"('{organization}', '{uuid4()}', '{case_id}', 'reported_problem', 'scale', '{actor}')")
            need_rows.append(f"('{organization}', '{uuid4()}', '{case_id}', 1, '{actor}', 'scale part', 1, 'each')")
            time_rows.append(
                f"('{organization}', '{uuid4()}', '{case_id}', '{actor}', 'on_site', now(), now(), 'timer')"
            )
            report_rows.append(
                "('{org}', '{id}', '{case}', 'PP-SCALE-{index}', '{actor}', '{actor}', '{actor}', 'worker', now(), "
                "'unit', 'Scale {index}', 'scale', '{{}}'::jsonb, false, 'routine', 'received', now(), 'local_fake', false, false)".format(
                    org=organization, id=uuid4(), case=case_id, index=index, actor=actor,
                )
            )
        _psql(
            "INSERT INTO maintenance_cases (organization_id, id, status, created_by) VALUES " + ",".join(case_rows),
            "perchpoint_phase2",
        )
        _psql(
            "INSERT INTO maintenance_case_events (organization_id, id, case_id, event_type, content, actor_id) VALUES " + ",".join(event_rows),
            "perchpoint_phase2",
        )
        _psql(
            "INSERT INTO maintenance_needs (organization_id, id, case_id, revision, author_actor, specification, quantity, unit_name) VALUES " + ",".join(need_rows),
            "perchpoint_phase2",
        )
        _psql(
            "INSERT INTO maintenance_time_intervals (organization_id, id, case_id, actor_id, category, started_at, ended_at, source) VALUES " + ",".join(time_rows),
            "perchpoint_phase2",
        )
        _psql(
            "INSERT INTO maintenance_reports (organization_id, id, case_id, public_reference, reporter_actor, resident_actor, entered_by, source, reported_at, place_kind, place_label, description, urgency, human_emergency, severity, summary, ack_due_at, environment, money_moved, real_values_activated) VALUES "
            + ",".join(report_rows),
            "perchpoint_phase2",
        )
    first = _psql(
        f"INSERT INTO maintenance_time_intervals (organization_id, id, case_id, actor_id, category, started_at, source) "
        f"SELECT '{organization}', '{uuid4()}', id, '{actor}', 'waiting', now(), 'timer' FROM maintenance_cases LIMIT 1 RETURNING id",
        "perchpoint_phase2",
    )
    second = _run([
        "docker", "exec", CONTAINER, "psql", "-v", "ON_ERROR_STOP=0",
        "-U", "postgres", "-d", "perchpoint_phase2", "-At", "-c",
        f"INSERT INTO maintenance_time_intervals (organization_id, id, case_id, actor_id, category, started_at, source) "
        f"SELECT '{organization}', '{uuid4()}', id, '{actor}', 'waiting', now(), 'timer' FROM maintenance_cases LIMIT 1",
    ], check=False)
    output = (second.stderr + second.stdout).lower()
    if "unique" not in output and "duplicate" not in output:
        raise RuntimeError("a second open timer was not refused")
    if not first:
        raise RuntimeError("the first open timer was not stored")
    samples = []
    for _ in range(20):
        started = time.perf_counter()
        count = _psql("SELECT count(*) FROM maintenance_reports WHERE severity = 'routine'", "perchpoint_phase2")
        samples.append((time.perf_counter() - started) * 1000)
        if int(count) < 200:
            raise RuntimeError(f"scale saw {count} reports")
    samples.sort()
    p95 = samples[int(0.95 * (len(samples) - 1))]
    print(f"queue_read_p95_ms={p95:.3f}")
    if p95 >= 300:
        raise RuntimeError(f"p95 {p95} exceeded 300")
    print("scale=passed")


def main() -> int:
    if "--execute" not in sys.argv:
        print("refusing to run without --execute")
        return 1
    _run(["docker", "rm", "-f", CONTAINER], check=False)
    try:
        _run([
            "docker", "run", "-d", "--name", CONTAINER, "-p", f"127.0.0.1:{PORT}:5432",
            "-e", "POSTGRES_USER=postgres", "-e", f"POSTGRES_PASSWORD={PASSWORD}", "-e", "POSTGRES_DB=postgres", IMAGE,
        ])
        _wait_ready()
        pinned = _env(PRIOR)
        _run([sys.executable, "-m", "perchpoint.bootstrap"], cwd=ROOT / "backend", env=pinned)
        version = _psql("SELECT version_num FROM alembic_version", "perchpoint_phase2")
        if version != PRIOR:
            raise RuntimeError(f"predecessor head was {version}")
        _run([sys.executable, "-m", "perchpoint.seed"], cwd=ROOT / "backend", env=pinned)
        marker = _psql("SELECT count(*) FROM accounts", "perchpoint_phase2")
        print(f"upgrade_from={version} accounts={marker}")
        _run([sys.executable, "-m", "alembic", "upgrade", HEAD], cwd=ROOT / "backend", env=_env(HEAD))
        version = _psql("SELECT version_num FROM alembic_version", "perchpoint_phase2")
        kept = _psql("SELECT count(*) FROM accounts", "perchpoint_phase2")
        if version != HEAD or kept != marker:
            raise RuntimeError(f"upgrade landed on {version} with accounts {kept}")
        role = _psql("SELECT rolsuper::text || ',' || rolbypassrls::text FROM pg_roles WHERE rolname = 'perchpoint_runtime'")
        forced = _psql(
            "SELECT count(*) FILTER (WHERE c.relforcerowsecurity) || '/' || count(*) "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity",
            "perchpoint_phase2",
        )
        print(f"migration_head={version} runtime={role} forced_rls={forced} accounts_preserved={kept}")
        if role != "false,false" or forced in {"226/226", "232/232"} or forced.startswith("0/"):
            raise RuntimeError("runtime role or forced row security is not the phase 20 count")
        pytest = _run(
            [sys.executable, "-m", "pytest", "tests/phase20", "-n", "0", "-q", "--tb=line"],
            cwd=ROOT / "backend",
            env=_env(None),
            check=False,
        )
        print(pytest.stdout[-4000:])
        if pytest.returncode:
            print(pytest.stderr[-4000:])
            return pytest.returncode
        _scale()
        print("clean_room=passed")
        return 0
    finally:
        _run(["docker", "rm", "-f", CONTAINER], check=False)


if __name__ == "__main__":
    sys.exit(main())

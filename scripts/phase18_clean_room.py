"""Prove Phase 18 from an empty disposable database, then remove it.

This container uses port 54344. It does not stop the presentation database on
54339, and it does not change the Phase 17 clean room's 0060 target.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE = "postgres:16@sha256:1a6ab3f5345eb6dbe04a1349529caabdb0ab09293a09590fad07b2246bfa4b54"
CONTAINER = os.environ.get("PHASE18_CLEAN_ROOM_CONTAINER", "perchpoint-phase18-cleanroom")
PASSWORD = "local-only-not-production"
PORT = os.environ.get("PHASE18_CLEAN_ROOM_PORT", "54344")
HEAD = "0064_phase18_return_completion"
ADMIN = f"postgresql+psycopg://postgres:{PASSWORD}@127.0.0.1:{PORT}/postgres"
MIGRATOR = f"postgresql+psycopg://perchpoint_migrator:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"
RUNTIME = f"postgresql+psycopg://perchpoint_runtime:{PASSWORD}@127.0.0.1:{PORT}/perchpoint_phase2"


def _run(command: list[str], *, cwd: Path = ROOT, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if check and completed.returncode:
        raise RuntimeError(f"{command} failed\n{completed.stdout[-4000:]}\n{completed.stderr[-4000:]}")
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
            "PHASE6_ALLOWED_ORIGINS": "http://127.0.0.1:3000,http://localhost:3000,http://testserver",
            "PHASE6_AUTH_URL": "http://127.0.0.1:9998",
            "PHASE6_PROVIDER_JWT_SECRET": "local-only-not-production-gotrue-jwt-secret",
            "PHASE6_SMTP_HOST": "127.0.0.1",
            "PHASE6_SMTP_PORT": "1125",
            "PHASE6_MAILPIT_URL": "http://127.0.0.1:8125",
            "PHASE5_SCANNER_MODE": "signature",
            "PHASE5_OBJECT_STORE": "filesystem",
            "PYTHONPATH": str(ROOT / "backend"),
        }
    )
    return env


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
        env = _env()
        _run([sys.executable, "-m", "perchpoint.bootstrap"], cwd=ROOT / "backend", env=env)
        version = _psql("SELECT version_num FROM alembic_version", "perchpoint_phase2")
        if version != HEAD:
            raise RuntimeError(f"clean room head was {version}")
        _run([sys.executable, "-m", "perchpoint.seed"], cwd=ROOT / "backend", env=env)
        _run([sys.executable, "-m", "perchpoint.seed"], cwd=ROOT / "backend", env=env)
        role = _psql("SELECT rolsuper::text || ',' || rolbypassrls::text FROM pg_roles WHERE rolname = 'perchpoint_runtime'")
        forced = _psql(
            "SELECT count(*) FILTER (WHERE c.relforcerowsecurity) || '/' || count(*) "
            "FROM pg_class c JOIN pg_namespace n ON n.oid = c.relnamespace "
            "WHERE n.nspname = 'public' AND c.relkind = 'r' AND c.relrowsecurity",
            "perchpoint_phase2",
        )
        print(f"migration_head={version} runtime={role} forced_rls={forced}")
        if role != "false,false" or "/" not in forced or forced.startswith("0/"):
            raise RuntimeError("runtime role or forced row security is not in force")
        selected = [arg for arg in sys.argv[1:] if arg != "--execute"]
        pytest_args = selected or ["tests/phase18"]
        pytest = _run(
            [sys.executable, "-m", "pytest", *pytest_args, "-n", "0", "-q", "--tb=line"],
            cwd=ROOT / "backend",
            env=env,
            check=False,
        )
        print(pytest.stdout[-4000:])
        if pytest.returncode:
            print(pytest.stderr[-4000:])
            return pytest.returncode
        print("clean_room=passed")
        return 0
    finally:
        _run(["docker", "rm", "-f", CONTAINER], check=False)


if __name__ == "__main__":
    raise SystemExit(main())

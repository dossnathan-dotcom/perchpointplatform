"""Prove Phase 8 from an empty disposable Compose project, then remove it.

The long-lived database and the acceptance project volumes are not this proof.
The acceptance project is stopped only while its published ports are borrowed,
and it is started again afterward. Its volumes are not removed.
"""
from __future__ import annotations

import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
COMPOSE_FILE = ROOT / "docker-compose.phase6-closeout.yml"
PROJECT = "perchpoint-phase9-cleanroom"
ACCEPT = "perchpoint-phase8-accept"
PASSWORD = "local-only-not-production"
ADMIN = f"postgresql+psycopg://postgres:{PASSWORD}@127.0.0.1:54339/postgres"
MIGRATOR = f"postgresql+psycopg://perchpoint_migrator:{PASSWORD}@127.0.0.1:54339/perchpoint_phase2"
RUNTIME = f"postgresql+psycopg://perchpoint_runtime:{PASSWORD}@127.0.0.1:54339/perchpoint_phase2"


def _run(command: list[str], *, cwd: Path = ROOT, env: dict | None = None, check: bool = True) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if check and completed.returncode:
        raise RuntimeError(f"{command} failed\n{completed.stdout}\n{completed.stderr}")
    return completed


def _compose(*arguments: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    return _run(["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE_FILE), *arguments], check=check)


def _psql(sql: str, database: str = "postgres") -> str:
    completed = _run(
        ["docker", "exec", f"{PROJECT}-postgres-1", "psql", "-v", "ON_ERROR_STOP=1", "-U", "postgres", "-d", database, "-At", "-c", sql]
    )
    return completed.stdout.strip()


def _wait_healthy(service: str, timeout: int) -> None:
    deadline = time.time() + timeout
    container = f"{PROJECT}-{service}-1"
    while time.time() < deadline:
        probe = _run(["docker", "inspect", "--format", "{{.State.Health.Status}}", container], check=False)
        if probe.returncode == 0 and probe.stdout.strip() == "healthy":
            print(f"healthy {container}")
            return
        time.sleep(2)
    raise RuntimeError(f"{container} did not become healthy")


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(
        {
            "PHASE2_ADMIN_URL": ADMIN.replace("/postgres", "/postgres"),
            "PHASE2_MIGRATOR_URL": MIGRATOR,
            "PHASE2_RUNTIME_URL": RUNTIME,
            "PHASE2_JWT_SECRET": "local-only-not-production-jwt-secret-32-plus",
            "PHASE2_DEV_PASSWORD": PASSWORD + "-password",
            "PHASE2_WEBHOOK_SECRET": PASSWORD + "-webhook",
            "PHASE6_ALLOW_DEV_JWT": "1",
            "PHASE6_AUTH_URL": "http://127.0.0.1:9998",
            "PHASE6_PROVIDER_JWT_SECRET": "local-only-not-production-gotrue-jwt-secret",
            "PHASE5_LIVE_SERVICES": "1",
            "PHASE5_OBJECT_STORE": "s3",
            "PHASE5_S3_ENDPOINT": "http://127.0.0.1:9100",
            "PHASE5_S3_ACCESS_KEY": PASSWORD,
            "PHASE5_S3_SECRET_KEY": PASSWORD,
            "PHASE5_S3_BUCKET": "perchpoint-documents",
            "PHASE5_SCANNER_MODE": "live",
            "PHASE5_CLAMAV_HOST": "127.0.0.1",
            "PHASE5_CLAMAV_PORT": "3410",
            "PYTHONPATH": str(ROOT / "backend"),
        }
    )
    env["PHASE2_ADMIN_URL"] = ADMIN
    return env


def _assert_removed() -> None:
    containers = _run(
        ["docker", "ps", "-a", "--filter", f"label=com.docker.compose.project={PROJECT}", "--format", "{{.ID}}"]
    ).stdout.strip()
    volumes = _run(
        ["docker", "volume", "ls", "--filter", f"label=com.docker.compose.project={PROJECT}", "--format", "{{.Name}}"]
    ).stdout.strip()
    print(f"containers={containers!r} volumes={volumes!r}")
    if containers or volumes:
        raise RuntimeError("clean-room resources remained after teardown")


def main() -> int:
    if "--execute" not in sys.argv:
        print("refusing to run without --execute")
        return 1
    accept_was_up = _run(["docker", "ps", "-q", "--filter", f"label=com.docker.compose.project={ACCEPT}"], check=False).stdout.strip()
    try:
        if accept_was_up:
            _run(["docker", "compose", "-p", ACCEPT, "-f", str(COMPOSE_FILE), "stop"])
        _compose("down", "--volumes", "--remove-orphans", check=False)
        _compose("up", "-d", "postgres")
        _wait_healthy("postgres", 90)
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
        _run([sys.executable, "-m", "alembic", "upgrade", "head"], cwd=ROOT / "backend", env=env)
        version = _psql("SELECT version_num FROM alembic_version", "perchpoint_phase2")
        lineage = _run([sys.executable, "scripts/phase6_migration_lineage.py", "--database-url", MIGRATOR], env=env)
        print(lineage.stdout)
        if "phase6_ancestry=confirmed" not in lineage.stdout or version != "0037_phase9_discovery":
            raise RuntimeError(f"lineage or head failed: {version}\n{lineage.stdout}")
        sys.path.insert(0, str(ROOT / "scripts"))
        from phase6_migration_lineage import PHASE6_REVISION, load_repository_graph

        graph = load_repository_graph(ROOT)
        seen: set[str] = set()
        cursor: str | None = version
        while isinstance(cursor, str) and cursor not in seen:
            seen.add(cursor)
            cursor = graph.get(cursor)
        if "0036_phase8_availability" not in seen or "0035_phase7_property_visibility" not in seen or PHASE6_REVISION not in seen:
            raise RuntimeError(f"required ancestors missing from {version}")
        print(f"ancestors=0036,0035,0031 lineage_length={len(seen)}")
        _run([sys.executable, "-m", "perchpoint.bootstrap"], cwd=ROOT / "backend", env=env)
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
        if role != "false,false":
            raise RuntimeError("runtime role is superuser or bypasses row security")
        _compose("up", "-d", "mailpit", "auth", "minio", "clamav")
        _wait_healthy("clamav", 360)
        _wait_healthy("minio", 90)
        pytest = _run([sys.executable, "-m", "pytest", "-q", "--tb=line"], cwd=ROOT / "backend", env=env)
        print(pytest.stdout[-4000:])
        if pytest.returncode:
            print(pytest.stderr[-4000:])
            return pytest.returncode
        print("clean_room=passed")
        return 0
    finally:
        _compose("down", "--volumes", "--remove-orphans", check=False)
        _assert_removed()
        if accept_was_up:
            _run(["docker", "compose", "-p", ACCEPT, "-f", str(COMPOSE_FILE), "start"], check=False)


if __name__ == "__main__":
    raise SystemExit(main())

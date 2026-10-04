"""Execute the destructive, disposable Phase 6 clean-room proof.

This script only operates on the dedicated ``perchpoint-phase6-cleanroom`` Compose
project. It writes ``clean-room.json`` only after every required command succeeds.
"""
from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from phase6_acceptance import CLEAN_ROOM_STEPS
from phase6_evidence_schema import (
    SCHEMA_VERSION,
    raw_artifact,
    sha256_text,
    source_provenance,
    validate_executions,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "test_reports" / "phase6"
COMPOSE_FILE = ROOT / "docker-compose.phase6-closeout.yml"
PROJECT = "perchpoint-phase6-cleanroom"
POSTGRES = f"{PROJECT}-postgres-1"
COMPOSE = ["docker", "compose", "-p", PROJECT, "-f", str(COMPOSE_FILE)]


class StepFailure(RuntimeError):
    pass


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _display(command: list[str]) -> str:
    return " ".join(shlex.quote(part) for part in command)


class Driver:
    def __init__(self) -> None:
        self.executions: list[dict] = []
        self.log = REPORTS / "clean-room.txt"
        self.log.parent.mkdir(parents=True, exist_ok=True)
        self.log.write_text("", encoding="utf-8")

    def step(
        self,
        name: str,
        commands: list[list[str]],
        *,
        env: dict[str, str] | None = None,
        require: str | tuple[str, ...] | None = None,
    ) -> str:
        if name not in CLEAN_ROOM_STEPS:
            raise StepFailure(f"unknown clean-room step: {name}")
        started = _now()
        output_parts: list[str] = []
        observed_parts: list[str] = []
        exit_code = 0
        for command in commands:
            completed = subprocess.run(
                command,
                cwd=ROOT,
                env=os.environ | (env or {}),
                text=True,
                encoding="utf-8",
                errors="replace",
                capture_output=True,
                check=False,
            )
            text = f"$ {_display(command)}\n{completed.stdout}\n{completed.stderr}".rstrip() + "\n"
            output_parts.append(text)
            observed_parts.append(completed.stdout + completed.stderr)
            with self.log.open("a", encoding="utf-8") as stream:
                stream.write(f"\n[{name}]\n{text}")
            if completed.returncode:
                exit_code = completed.returncode
                break
        output = "".join(output_parts)
        markers = (require,) if isinstance(require, str) else (require or ())
        if any(marker not in "".join(observed_parts) for marker in markers):
            exit_code = exit_code or 1
            output += f"\nrequired marker absent: {markers}\n"
        raw_path = REPORTS / "raw" / "clean-room" / f"{len(self.executions) + 1:02d}-{name}.log"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_text(output, encoding="utf-8")
        self.executions.append(
            {
                "step": name,
                "command": " && ".join(_display(command) for command in commands),
                "started_at": started,
                "finished_at": _now(),
                "exit_code": exit_code,
                "output_sha256": sha256_text(output),
                "output_bytes": len(output.encode("utf-8")),
                "output_path": raw_path.relative_to(ROOT).as_posix(),
            }
        )
        if exit_code:
            raise StepFailure(f"{name} failed; see {self.log}")
        return output


def _compose(*arguments: str) -> list[str]:
    return [*COMPOSE, *arguments]


def _psql(sql: str, database: str = "postgres") -> list[str]:
    return [
        "docker", "exec", POSTGRES, "psql", "-v", "ON_ERROR_STOP=1",
        "-U", "postgres", "-d", database, "-At", "-c", sql,
    ]


def _runtime_psql(sql: str) -> list[str]:
    return [
        "docker", "exec", "-e", "PGPASSWORD=local-only-not-production", POSTGRES,
        "psql", "-v", "ON_ERROR_STOP=1", "-U", "perchpoint_runtime",
        "-d", "perchpoint_phase2", "-At", "-c", sql,
    ]


def _wait_postgres() -> list[str]:
    return _compose(
        "exec", "-T", "postgres", "sh", "-ec",
        "i=0; until pg_isready -U postgres; do i=$((i+1)); [ $i -lt 60 ] || exit 1; sleep 1; done",
    )


def _pytest(*nodes: str, live: bool = False) -> list[str]:
    command = _compose(
        "run", "--rm", "--no-deps",
        *(("-e", "PHASE5_LIVE_SERVICES=1") if live else ()),
        "migrate", "python", "-m", "pytest", "-q", "--tb=line", *nodes,
    )
    return command


def _full_pytest() -> list[str]:
    return _compose(
        "run",
        "--rm",
        "--no-deps",
        "--volume",
        f"{ROOT}:/workspace",
        "--workdir",
        "/workspace/backend",
        "migrate",
        "python",
        "-m",
        "pytest",
        "-q",
        "--tb=line",
        "tests",
    )


def _wait_url(url: str) -> list[str]:
    source = (
        "import sys,time,urllib.request\n"
        f"url={url!r}\n"
        "last=None\n"
        "for _ in range(120):\n"
        " try:\n"
        "  with urllib.request.urlopen(url,timeout=3) as r:\n"
        "   print(f'ready status={r.status} url={url}');sys.exit(0)\n"
        " except Exception as e:last=e;time.sleep(2)\n"
        "print(f'not ready: {last}',file=sys.stderr);sys.exit(1)\n"
    )
    return [sys.executable, "-c", source]


def _wait_health(container: str) -> list[str]:
    source = (
        "import subprocess,sys,time\n"
        f"name={container!r}\n"
        "for _ in range(120):\n"
        " p=subprocess.run(['docker','inspect','--format','{{.State.Health.Status}}',name],text=True,capture_output=True)\n"
        " if p.returncode==0 and p.stdout.strip()=='healthy':print(f'healthy {name}');sys.exit(0)\n"
        " time.sleep(2)\n"
        "print(f'not healthy: {name}',file=sys.stderr);sys.exit(1)\n"
    )
    return [sys.executable, "-c", source]


def _verify_sign_in() -> list[str]:
    source = (
        "import json,urllib.request\n"
        "body=json.dumps({'email':'ann.synthetic@example.com','password':'local-only-not-production-password'}).encode()\n"
        "request=urllib.request.Request('http://127.0.0.1:8010/api/v2/auth/sign-in',data=body,headers={'content-type':'application/json'},method='POST')\n"
        "with urllib.request.urlopen(request,timeout=10) as response:\n"
        " print(f'sign_in_ready status={response.status}')\n"
    )
    return [sys.executable, "-c", source]


def _migration_env(database: str) -> list[str]:
    prefix = "postgresql+psycopg://"
    return [
        "-e", f"PHASE2_MIGRATOR_URL={prefix}perchpoint_migrator:local-only-not-production@postgres:5432/{database}",
        "-e", f"PHASE2_RUNTIME_URL={prefix}perchpoint_runtime:local-only-not-production@postgres:5432/{database}",
    ]


def _idempotent_seed_command() -> list[str]:
    counts = _psql(
        "SELECT json_build_array((SELECT count(*) FROM organizations),(SELECT count(*) FROM accounts),(SELECT count(*) FROM memberships));",
        "perchpoint_phase2",
    )
    seed = _compose("run", "--rm", "--no-deps", "seed")
    source = (
        "import subprocess,sys\n"
        f"counts={counts!r};seed={seed!r};cwd={str(ROOT)!r}\n"
        "before=subprocess.check_output(counts,cwd=cwd,text=True).strip()\n"
        "completed=subprocess.run(seed,cwd=cwd)\n"
        "after=subprocess.check_output(counts,cwd=cwd,text=True).strip()\n"
        "print(f'before={before} after={after}')\n"
        "sys.exit(0 if completed.returncode==0 and before==after else 1)\n"
    )
    return [sys.executable, "-c", source]


def _assert_project_removed() -> list[str]:
    source = (
        "import subprocess,sys\n"
        f"project={PROJECT!r}\n"
        "containers=subprocess.check_output(['docker','ps','-a','--filter',f'label=com.docker.compose.project={project}','--format','{{.ID}}'],text=True).strip()\n"
        "volumes=subprocess.check_output(['docker','volume','ls','--filter',f'label=com.docker.compose.project={project}','--format','{{.Name}}'],text=True).strip()\n"
        "print(f'containers={containers!r} volumes={volumes!r}')\n"
        "sys.exit(1 if containers or volumes else 0)\n"
    )
    return [sys.executable, "-c", source]


def run() -> dict:
    provenance = source_provenance(ROOT)
    driver = Driver()
    commit = provenance["commit"]
    failed_path = REPORTS / "clean-room.failed.json"
    final_path = REPORTS / "clean-room.json"
    final_path.unlink(missing_ok=True)
    try:
        driver.step("compose-config", [_compose("config", "--quiet")])
        driver.step("image-build", [_compose("build", "--pull", "migrate", "web")])
        driver.step(
            "non-root",
            [
                ["docker", "run", "--rm", "--entrypoint", "id", "perchpoint-api:phase6", "-u"],
                ["docker", "run", "--rm", "--entrypoint", "id", "perchpoint-web:phase6", "-u"],
            ],
            require="10001",
        )
        subprocess.run(_compose("down", "--volumes", "--remove-orphans"), cwd=ROOT, check=False, capture_output=True)
        init_sql = (
            "CREATE ROLE perchpoint_migrator LOGIN NOBYPASSRLS NOSUPERUSER PASSWORD 'local-only-not-production';"
            "CREATE ROLE perchpoint_runtime LOGIN NOBYPASSRLS NOSUPERUSER PASSWORD 'local-only-not-production';"
            "CREATE ROLE perchpoint_definer NOLOGIN BYPASSRLS NOSUPERUSER;"
        )
        grants = (
            "GRANT CONNECT,CREATE ON DATABASE perchpoint_phase2 TO perchpoint_migrator;"
            "GRANT CONNECT ON DATABASE perchpoint_phase2 TO perchpoint_runtime;"
        )
        driver.step(
            "empty-migrate",
            [
                _compose("up", "-d", "postgres"),
                _wait_postgres(),
                _psql(init_sql),
                _psql("CREATE DATABASE perchpoint_phase2;"),
                _psql(grants),
                _psql("GRANT ALL ON SCHEMA public TO perchpoint_migrator; GRANT perchpoint_definer TO perchpoint_migrator;", "perchpoint_phase2"),
                _compose("run", "--rm", "--no-deps", "migrate", "python", "-m", "alembic", "upgrade", "head"),
                _psql("SELECT version_num FROM alembic_version;", "perchpoint_phase2"),
            ],
            require="0031_phase6_authz_remediation",
        )
        upgrade_db = "perchpoint_phase5_upgrade"
        driver.step(
            "phase5-upgrade",
            [
                _psql(f"CREATE DATABASE {upgrade_db};"),
                _psql(f"GRANT CONNECT,CREATE ON DATABASE {upgrade_db} TO perchpoint_migrator;"),
                _psql("GRANT ALL ON SCHEMA public TO perchpoint_migrator; GRANT perchpoint_definer TO perchpoint_migrator;", upgrade_db),
                _compose("run", "--rm", "--no-deps", *_migration_env(upgrade_db), "migrate", "python", "-m", "alembic", "upgrade", "0011_phase5_hold_guard"),
                _compose("run", "--rm", "--no-deps", *_migration_env(upgrade_db), "migrate", "python", "-m", "alembic", "upgrade", "head"),
                _psql("SELECT version_num FROM alembic_version;", upgrade_db),
            ],
            require="0031_phase6_authz_remediation",
        )
        driver.step(
            "forced-rls",
            [_psql("SELECT CASE WHEN count(*) FILTER (WHERE c.relrowsecurity)>0 AND count(*) FILTER (WHERE c.relrowsecurity AND NOT c.relforcerowsecurity)=0 THEN 'forced_rls_ok' ELSE 'forced_rls_bad' END FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public' AND c.relkind='r';", "perchpoint_phase2")],
            require="forced_rls_ok",
        )
        driver.step(
            "restricted-roles",
            [_psql("SELECT rolname,rolsuper,rolbypassrls,rolcanlogin FROM pg_roles WHERE rolname IN ('perchpoint_runtime','perchpoint_migrator','perchpoint_definer') ORDER BY rolname;")],
            require="perchpoint_runtime|f|f|t",
        )
        driver.step("seed-once", [_compose("run", "--rm", "--no-deps", "seed")])
        driver.step("seed-idempotent", [_idempotent_seed_command()], require="before=")
        driver.step(
            "auth-health",
            [
                _compose("up", "-d", "mailpit", "auth-db-init", "auth", "minio", "clamav", "api", "worker", "web"),
                _wait_url("http://127.0.0.1:9998/health"),
                _wait_url("http://127.0.0.1:8010/api/v2/health/ready"),
                _verify_sign_in(),
                [sys.executable, "scripts/phase6_evidence.py", "rls"],
            ],
            require=("status=200", "sign_in_ready status=200"),
        )
        driver.step("full-backend", [_full_pytest()], require="passed")
        driver.step("mailpit", [_wait_url("http://127.0.0.1:8125/api/v1/info")], require="status=200")
        driver.step("minio-live", [_pytest("tests/phase5/test_live_services.py::test_live_minio_presign_is_private_and_cleaned_up", live=True)], require="1 passed")
        driver.step("clamav-live", [_pytest("tests/phase5/test_live_services.py::test_live_clamav_detects_eicar_and_outage_is_not_clean", live=True)], require="1 passed")
        identity = "tests/phase6/test_identity.py::"
        driver.step("sign-in", [_pytest(identity + "test_interactive_sign_in_uses_cookie_and_rejects_missing_csrf")], require="1 passed")
        driver.step("totp", [_pytest(identity + "test_invitation_is_single_use_and_totp_secret_is_not_stored_in_plaintext")], require="1 passed")
        driver.step("invitation", [_pytest(identity + "test_resident_cannot_use_staff_invitation_route", identity + "test_privileged_roles_cannot_be_created_through_invitations")], require="2 passed")
        driver.step("password-reset", [_pytest(identity + "test_password_reset_does_not_sign_in_and_rejects_replay")], require="1 passed")
        driver.step("sessions", [_pytest(identity + "test_sessions_access_requests_and_self_recovery_are_enforced", identity + "test_provider_refresh_reuse_revokes_the_application_session")], require="2 passed")
        driver.step("context", [_pytest(identity + "test_origin_is_bound_to_the_session_csrf_token", identity + "test_runtime_role_without_actor_context_sees_no_identity_rows")], require="2 passed")
        driver.step("delegation", [_pytest(identity + "test_delegation_usage_enforces_scope_decision_amount_and_split_detection")], require="1 passed")
        driver.step("owner-threshold", [_pytest(identity + "test_financial_thresholds_and_authority_boundaries")], require="1 passed")
        driver.step("vendor-isolation", [_pytest(identity + "test_vendor_admin_proposes_operations_approves_and_worker_assignment_activates", identity + "test_restricted_rls_enforces_household_and_worker_assignment_relationships")], require="2 passed")
        driver.step("search-export-storage", [_pytest("tests/phase5/test_canonical.py::test_search_does_not_leak_another_organization", "tests/phase5/test_live_journey.py::test_live_api_access_export_and_ocr", live=True)], require="2 passed")
        driver.step("audit-lineage", [_pytest(identity + "test_maintenance_recommendation_and_management_variance_are_append_only")], require="1 passed")
        driver.step("worker", [_compose("ps", "worker"), _compose("exec", "-T", "worker", "python", "-m", "perchpoint.worker")])
        browser_env = {
            "PLAYWRIGHT_BASE_URL": "http://127.0.0.1:3010",
            "PLAYWRIGHT_SKIP_WEBSERVER": "1",
            "PHASE2_DEV_PASSWORD": "local-only-not-production-password",
            "PHASE6_BROWSER_ORIGIN": "http://127.0.0.1:3010",
            "PHASE6_AUTH_URL": "http://127.0.0.1:9998",
            "PHASE6_MAILPIT_URL": "http://127.0.0.1:8125",
            "PHASE6_PROVIDER_JWT_SECRET": "local-only-not-production-gotrue-jwt-secret",
            "PHASE6_PROVIDER_ISSUER": "perchpoint-local-auth",
        }
        driver.step("browser", [[sys.executable, "scripts/phase6_browser_evidence.py"]], env=browser_env, require="passed")
        driver.step("accessibility", [[sys.executable, "scripts/phase6_acceptance.py", "--validate-report", "accessibility.json"]])
        driver.step(
            "responsive",
            [
                [sys.executable, "scripts/phase6_acceptance.py", "--validate-report", "responsive.json"],
                [sys.executable, "scripts/phase6_evidence.py", "frontend"],
            ],
        )
        for step, service, url in (
            ("restart-auth", "auth", "http://127.0.0.1:9998/health"),
            ("restart-api", "api", "http://127.0.0.1:8010/api/v2/health/ready"),
            ("restart-worker", "worker", None),
        ):
            commands = [_compose("restart", service)]
            commands.append(_wait_url(url) if url else _wait_health(f"{PROJECT}-worker-1"))
            driver.step(step, commands)
        revocation_sql = "WITH changed AS (UPDATE identity_sessions SET revoked_at=now() WHERE id=(SELECT id FROM identity_sessions ORDER BY created_at LIMIT 1) RETURNING id) SELECT CASE WHEN count(*)=1 THEN 'revocation_written' ELSE 'revocation_missing' END FROM changed;"
        membership_sql = "WITH changed AS (UPDATE memberships SET ended_at=now() WHERE id=(SELECT id FROM memberships WHERE ended_at IS NULL ORDER BY effective_at LIMIT 1) RETURNING id) SELECT CASE WHEN count(*)=1 THEN 'membership_ended' ELSE 'membership_missing' END FROM changed;"
        driver.step("persistent-revocation", [_psql(revocation_sql, "perchpoint_phase2")], require="revocation_written")
        driver.step("persistent-membership", [_psql(membership_sql, "perchpoint_phase2")], require="membership_ended")
        driver.step(
            "restart-postgres",
            [
                _compose("restart", "postgres"),
                _wait_postgres(),
                _psql("SELECT CASE WHEN EXISTS(SELECT 1 FROM identity_sessions WHERE revoked_at IS NOT NULL) AND EXISTS(SELECT 1 FROM memberships WHERE ended_at IS NOT NULL) THEN 'persistence_ok' ELSE 'persistence_missing' END;", "perchpoint_phase2"),
                _runtime_psql("SELECT set_config('app.actor_id',(SELECT account_id::text FROM memberships WHERE ended_at IS NOT NULL ORDER BY ended_at DESC LIMIT 1),false),set_config('app.organization_id',(SELECT organization_id::text FROM memberships WHERE ended_at IS NOT NULL ORDER BY ended_at DESC LIMIT 1),false); SELECT CASE WHEN count(*)=0 THEN 'membership_denied' ELSE 'membership_leaked' END FROM properties;"),
            ],
            require=("persistence_ok", "membership_denied"),
        )
        outage_probe = [sys.executable, "-c", "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8010/api/v2/health/ready',timeout=5)"]
        driver.step(
            "fail-closed-outage",
            [
                _compose("stop", "postgres"),
                [sys.executable, "-c", "import subprocess,sys;p=subprocess.run(sys.argv[1:]);print('denied' if p.returncode else 'unexpected success');sys.exit(0 if p.returncode else 1)", *outage_probe],
                _compose("start", "postgres"),
                _wait_postgres(),
            ],
            require="denied",
        )
        driver.step("teardown", [_compose("down", "--volumes", "--remove-orphans")])
        driver.step(
            "disposable-removed",
            [_assert_project_removed()],
            require="containers='' volumes=''",
        )
        errors = validate_executions({"executions": driver.executions}, CLEAN_ROOM_STEPS)
        if errors:
            raise StepFailure("; ".join(errors))
        report = {
            "schema_version": SCHEMA_VERSION,
            "kind": "clean-room",
            "commit": commit,
            "tree_hash": provenance["tree_hash"],
            "source_clean": provenance["source_clean"],
            "command": "python scripts/phase6_clean_room.py --execute",
            "timestamp": _now(),
            "exit_code": 0,
            "totals": {"total": len(CLEAN_ROOM_STEPS), "passed": len(CLEAN_ROOM_STEPS), "failed": 0, "skipped": 0},
            "steps": list(CLEAN_ROOM_STEPS),
            "executions": driver.executions,
            "project": PROJECT,
            "empty_volumes": True,
            "volumes_removed": True,
            "raw_artifacts": [
                raw_artifact(ROOT, ROOT / execution["output_path"])
                for execution in driver.executions
            ],
        }
        write_json(final_path, report)
        failed_path.unlink(missing_ok=True)
        return report
    except Exception as exc:
        if os.environ.get("PHASE6_KEEP_FAILED_CLEANROOM") != "1":
            subprocess.run(
                _compose("down", "--volumes", "--remove-orphans"),
                cwd=ROOT,
                check=False,
                capture_output=True,
            )
        write_json(
            failed_path,
            {
                "schema_version": SCHEMA_VERSION,
                "kind": "clean-room-attempt",
                "commit": commit,
                "command": "python scripts/phase6_clean_room.py --execute",
                "timestamp": _now(),
                "exit_code": 1,
                "error": str(exc),
                "executions": driver.executions,
            },
        )
        raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--execute", action="store_true", help="acknowledge destructive removal of the dedicated clean-room project")
    args = parser.parse_args()
    if not args.execute:
        raise SystemExit("refusing to run without --execute")
    report = run()
    print(f"phase6 clean-room passed: {report['totals']['passed']} steps")


if __name__ == "__main__":
    main()

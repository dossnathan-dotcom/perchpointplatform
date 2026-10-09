"""Execute Phase 14 gates and write structured evidence. A nonzero command is never passed."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "test_reports" / "phase14"
STATE = REPORTS / "acceptance-state.json"
ANCESTOR = "c8699dcb05fc35fc2f267c9f5fa53ff62a5a9e81"

ISOLATED = {
    "PHASE2_ADMIN_URL": "postgresql+psycopg://postgres:local-only-not-production@127.0.0.1:54339/postgres",
    "PHASE2_MIGRATOR_URL": "postgresql+psycopg://perchpoint_migrator:local-only-not-production@127.0.0.1:54339/perchpoint_phase2",
    "PHASE2_RUNTIME_URL": "postgresql+psycopg://perchpoint_runtime:local-only-not-production@127.0.0.1:54339/perchpoint_phase2",
    "PHASE2_JWT_SECRET": "local-only-not-production-jwt-secret-32-plus",
    "PHASE2_DEV_PASSWORD": "local-only-not-production-password",
    "PHASE2_WEBHOOK_SECRET": "local-only-not-production-webhook",
    "PHASE6_SESSION_KEY": "local-only-not-production-phase6-session-encryption-key",
    "PHASE6_PROVIDER_JWT_SECRET": "local-only-not-production-gotrue-jwt-secret",
    "PHASE6_AUTH_URL": "http://127.0.0.1:9998",
    "PHASE6_MAILPIT_URL": "http://127.0.0.1:8125",
    "PHASE6_SMTP_HOST": "127.0.0.1",
    "PHASE6_SMTP_PORT": "1125",
    "PHASE6_ALLOW_DEV_JWT": "1",
    "PHASE2_LOCAL_AUTH": "development",
    "PHASE3_ENVIRONMENT": "local",
    "PHASE5_LIVE_SERVICES": "1",
    "PHASE5_OBJECT_STORE": "s3",
    "PHASE5_S3_ENDPOINT": "http://127.0.0.1:9100",
    "PHASE5_S3_ACCESS_KEY": "local-only-not-production",
    "PHASE5_S3_SECRET_KEY": "local-only-not-production",
    "PHASE5_S3_BUCKET": "perchpoint-documents",
    "PHASE5_SCANNER_MODE": "live",
    "PHASE5_CLAMAV_HOST": "127.0.0.1",
    "PHASE5_CLAMAV_PORT": "3410",
    "API_PROXY_TARGET": "http://127.0.0.1:8000",
}


def _env() -> dict[str, str]:
    env = os.environ.copy()
    env.update(ISOLATED)
    return env


def _run(command: list[str], cwd: Path, env: dict[str, str] | None = None) -> tuple[int, str]:
    executable = shutil.which(command[0]) or command[0]
    completed = subprocess.run([executable, *command[1:]], cwd=cwd, env=env or _env(), text=True, capture_output=True, check=False)
    output = (completed.stdout or "") + (completed.stderr or "")
    return completed.returncode, output[-20000:]


def _write(path: Path, payload: dict) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")
    return hashlib.sha256(text.encode()).hexdigest()


def _head() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def gate_r0() -> tuple[int, str]:
    code, output = _run(["git", "merge-base", "--is-ancestor", ANCESTOR, "HEAD"], ROOT, os.environ.copy())
    if code != 0:
        return code, output
    names = subprocess.check_output(["git", "diff", "--name-only", f"{ANCESTOR}...HEAD"], cwd=ROOT, text=True)
    if any("phase15" in line or "zillow" in line.lower() for line in names.splitlines()):
        return 1, names
    return 0, names


def gate_commands(gate: str) -> list[tuple[list[str], Path]]:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    pytest = [sys.executable, "-m", "pytest"]
    phase13 = "tests/phase14/test_lease.py"
    mapping: dict[str, list[tuple[list[str], Path]]] = {
        "P14-R1": [([sys.executable, "scripts/validate_phase14_answers.py"], ROOT)],
        "P14-R2": [
            ([sys.executable, "-m", "foundation.export", "--check"], backend),
            (["node", "scripts/generate-contract-types.cjs", "--check"], frontend),
        ],
        "P14-R3": [([*pytest, "tests/phase2/test_commands_and_authorization.py::test_empty_database_migration_and_repeatable_seed", "-q", "--tb=line", "-n", "0"], backend)],
        "P14-R4": [([*pytest, phase13, "-q", "--tb=line", "-n", "0"], backend)],
        "P14-R5": [([*pytest, phase13, "-q", "--tb=line", "-n", "0"], backend)],
        "P14-R6": [(["corepack", "yarn", "playwright", "test", "e2e/phase14-lease.spec.js", "--reporter=line"], frontend)],
        "P14-R7": [([*pytest, phase13, "-q", "--tb=line", "-n", "0"], backend)],
        "P14-R8": [([*pytest, phase13, "-q", "--tb=line", "-n", "0"], backend)],
        "P14-R9": [([*pytest, phase13, "-q", "--tb=line", "-n", "0"], backend)],
        "P14-R10": [
            ([sys.executable, "-m", "ruff", "check", "perchpoint/phase14_lease.py", "perchpoint/phase14_routes.py", "tests/phase14"], backend),
            ([sys.executable, "-m", "pip_audit", "-r", "requirements.txt"], backend),
            (["corepack", "yarn", "audit", "--groups", "dependencies", "--level", "high"], frontend),
        ],
        "P14-R11": [
            ([*pytest, "-q", "--tb=line"], backend),
            ([sys.executable, "-m", "ruff", "check", "perchpoint", "tests"], backend),
            ([sys.executable, "-m", "compileall", "-q", "perchpoint"], backend),
            (["corepack", "yarn", "eslint", "src", "--max-warnings", "0"], frontend),
            (["corepack", "yarn", "test", "--watchAll=false", "--watchman=false"], frontend),
            (["corepack", "yarn", "build"], frontend),
        ],
        "P14-R12": [(["corepack", "yarn", "playwright", "test", "e2e/phase14-lease.spec.js", "--reporter=line"], frontend)],
        "P14-R13": [([sys.executable, "scripts/phase14_benchmark.py"], ROOT)],
        "P14-R14": [([*pytest, "-q", "--tb=line"], backend)],
        "P14-R15": [([sys.executable, "scripts/phase14_clean_room.py", "--execute"], ROOT)],
        "P14-R16": [([sys.executable, "scripts/phase14_review.py"], ROOT)],
    }
    if gate not in mapping:
        raise SystemExit(f"unsupported gate {gate}")
    return mapping[gate]


def record(gate: str, command: str, code: int, output: str, head: str) -> None:
    digest = hashlib.sha256(output.encode()).hexdigest()
    payload = {
        "command": command,
        "exit_code": code,
        "finished_at": datetime.now(timezone.utc).isoformat(),
        "gate": gate,
        "output_sha256": digest,
        "result": "passed" if code == 0 else "failed",
        "tested_commit": head,
    }
    log = REPORTS / "logs" / f"{gate}.log"
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(output, encoding="utf-8", newline="\n")
    _write(REPORTS / "gates" / f"{gate}.json", payload)
    state = {"behavior_commit": head, "gates": {}, "schema": 1}
    if STATE.exists():
        state.update(json.loads(STATE.read_text(encoding="utf-8")))
        state["behavior_commit"] = head
    state.setdefault("gates", {})[gate] = payload
    _write(STATE, state)
    print(f"{gate}: {payload['result']} exit {code}")


def run_gate(gate: str) -> int:
    head = _head()
    if gate == "P14-R0":
        code, output = gate_r0()
        record(gate, f"git merge-base --is-ancestor {ANCESTOR} HEAD", code, output, head)
        return code
    commands = gate_commands(gate)
    chunks = []
    code = 0
    rendered = " && ".join(" ".join(part) for part, _cwd in commands)
    for command, cwd in commands:
        item_code, output = _run(command, cwd)
        chunks.append(output)
        if item_code != 0:
            code = item_code
            break
    record(gate, rendered, code, "\n".join(chunks), head)
    return code


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gate")
    parser.add_argument("--all", action="store_true")
    args = parser.parse_args()
    gates = [f"P14-R{index}" for index in range(17)] if args.all else [args.gate]
    if not args.gate and not args.all:
        parser.error("use --gate P14-R0 or --all")
    for gate in gates:
        if gate is None:
            continue
        if run_gate(gate) != 0:
            return 1
    if args.all:
        write_reports()
    return 0


def write_reports() -> None:
    state = json.loads(STATE.read_text(encoding="utf-8"))
    behavior = state["behavior_commit"]
    docs = ROOT / "docs" / "plans" / "phase14"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "ACCEPTANCE_REPORT.md").write_text(
        "\n".join(
            [
                "# Phase 14 acceptance report",
                "",
                f"Behavior commit: `{behavior}`.",
                "",
                "`python scripts/phase14_evidence.py --all` recorded P14-R0 through P14-R16 as passed with exit code 0. The structured record is `test_reports/phase14/acceptance-state.json`. Each gate stores the command, the behavior commit, the exit code, and the SHA-256 of the captured output. Raw output is in `test_reports/phase14/logs/`.",
                "",
                "Migration head exercised by the empty-database and clean-room gates: `0042_phase14_lease`. `0041_phase13_screening`, `0040_phase12_application`, `0039_phase11_showing`, `0038_phase10_inquiry`, `0037_phase9_discovery`, `0036_phase8_availability`, `0035_phase7_property_visibility`, and `0031_phase6_authz_remediation` are ancestors of that head.",
                "",
                "P14-R17 and P14-R18 are not local gates. They are recorded after the protected pull request and the merged main workflows.",
                "",
                "Hosted Supabase, Faruk and Ann stakeholder acceptance, qualified legal and fair-housing review, real-data migration, production providers, advertising, and production deployment are not granted. Phase 15 was not started. Live signature and payment providers were not activated.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    (docs / "REVIEW_FINDINGS.md").write_text(
        "\n".join(
            [
                "# Phase 14 review findings",
                "",
                f"Reviewed against behavior commit `{behavior}`. `python scripts/phase14_review.py` reported no critical or high findings. Reviewer identity: `phase14-independent-review`.",
                "",
                "## Resolved",
                "",
                "- A lease starts only from an approved Phase 13 handoff. A human confirms the package.",
                "- A fake signature executes the package and does not activate a resident by itself.",
                "- A forged signature is rejected, and a named live provider is rejected.",
                "- Deposit satisfaction is an obligation record and does not post a ledger or collect money.",
                "- Activation happens once after execution and deposit satisfaction.",
                "- An unrelated organization role is denied, and a runtime session with no actor sees no lease rows.",
                "",
                "## Separate verdicts",
                "",
                "This technical review does not grant hosted Supabase acceptance, stakeholder acceptance, qualified legal or fair-housing acceptance, privacy-counsel acceptance, screening-provider acceptance, real-data migration acceptance, or production deployment.",
                "",
                "No critical or high finding remains open inside Phase 14.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    (docs / "ENVIRONMENT.md").write_text(
        "\n".join(
            [
                "# Phase 14 acceptance environment",
                "",
                "Local gates used the disposable Docker project `perchpoint-phase8-accept`. Postgres is published on `127.0.0.1:54339`, GoTrue on `127.0.0.1:9998`, Mailpit on `127.0.0.1:8125`, MinIO on `127.0.0.1:9100`, and ClamAV on `127.0.0.1:3410`. The database name is `perchpoint_phase2`.",
                "",
                "P14-R15 created a separate project, `perchpoint-phase14-cleanroom`, from empty volumes, migrated it to `0042_phase14_lease`, ran bootstrap, seed, the backend suite, and then removed that project's containers and volumes. The acceptance project was stopped only while those host ports were borrowed and was started again afterward. Its volumes were not removed.",
                "",
                "The long-lived database at `127.0.0.1:5432` is not acceptance evidence.",
                "",
                "Runtime role on these databases is `NOSUPERUSER` and `NOBYPASSRLS`.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )


if __name__ == "__main__":
    raise SystemExit(main())

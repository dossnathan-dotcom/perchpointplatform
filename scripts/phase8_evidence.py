"""Execute Phase 8 gates and write structured evidence. A nonzero command is never passed."""
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
REPORTS = ROOT / "test_reports" / "phase8"
STATE = REPORTS / "acceptance-state.json"
ANCESTOR = "1a4e1c25880df87eb9fb0f81c186de1b67294477"

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
    if any("phase9" in line or "phase10" in line for line in names.splitlines()):
        return 1, names
    return 0, names


def gate_commands(gate: str) -> list[tuple[list[str], Path]]:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    pytest = [sys.executable, "-m", "pytest"]
    phase8 = "tests/phase8/test_property_availability.py"
    mapping: dict[str, list[tuple[list[str], Path]]] = {
        "P8-R1": [([sys.executable, "scripts/validate_phase8_answers.py"], ROOT)],
        "P8-R2": [
            ([sys.executable, "-m", "foundation.export", "--check"], backend),
            (["node", "scripts/generate-contract-types.cjs", "--check"], frontend),
        ],
        "P8-R3": [([*pytest, "tests/phase2/test_commands_and_authorization.py::test_empty_database_migration_and_repeatable_seed", "-q", "--tb=line", "-n", "0"], backend)],
        "P8-R4": [([*pytest, phase8, "-q", "--tb=line", "-k", "runtime or inventory", "-n", "0"], backend)],
        "P8-R5": [([*pytest, phase8, "-q", "--tb=line", "-n", "0"], backend)],
        "P8-R6": [([*pytest, "tests/phase7/test_public_content.py", "-q", "--tb=line", "-k", "published or public", "-n", "0"], backend)],
        "P8-R7": [([*pytest, phase8 + "::test_portfolio_truth_publication_and_denial", "-q", "--tb=line", "-n", "0"], backend)],
        "P8-R8": [([*pytest, "tests/phase5/test_live_services.py", "-q", "--tb=line", "-n", "0"], backend)],
        "P8-R9": [([*pytest, phase8 + "::test_portfolio_truth_publication_and_denial", "-q", "--tb=line", "-n", "0"], backend)],
        "P8-R10": [
            ([sys.executable, "-m", "ruff", "check", "perchpoint/phase8_portfolio.py", "perchpoint/phase8_routes.py", "tests/phase8"], backend),
            ([sys.executable, "-m", "pip_audit", "-r", "requirements.txt"], backend),
            (["corepack", "yarn", "audit", "--groups", "dependencies", "--level", "high"], frontend),
        ],
        "P8-R11": [
            ([*pytest, "-q", "--tb=line"], backend),
            ([sys.executable, "-m", "ruff", "check", "perchpoint", "tests"], backend),
            ([sys.executable, "-m", "compileall", "-q", "perchpoint"], backend),
            (["corepack", "yarn", "eslint", "src", "--max-warnings", "0"], frontend),
            (["corepack", "yarn", "test", "--watchAll=false", "--watchman=false"], frontend),
            (["corepack", "yarn", "build"], frontend),
        ],
        "P8-R12": [(["corepack", "yarn", "playwright", "test", "e2e/phase8-portfolio.spec.js", "--reporter=line"], frontend)],
        "P8-R13": [(["corepack", "yarn", "playwright", "test", "e2e/phase8-portfolio.spec.js", "--reporter=line"], frontend)],
        "P8-R14": [([sys.executable, "scripts/phase8_benchmark.py"], ROOT)],
        "P8-R15": [([sys.executable, "scripts/phase8_clean_room.py", "--execute"], ROOT)],
        "P8-R16": [([sys.executable, "scripts/phase8_review.py"], ROOT)],
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
    if gate == "P8-R0":
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
    gates = [f"P8-R{index}" for index in range(17)] if args.all else [args.gate]
    if not args.gate and not args.all:
        parser.error("use --gate P8-R0 or --all")
    for gate in gates:
        if gate is None:
            continue
        if run_gate(gate) != 0:
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

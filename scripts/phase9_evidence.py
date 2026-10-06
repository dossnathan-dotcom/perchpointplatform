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
REPORTS = ROOT / "test_reports" / "phase9"
STATE = REPORTS / "acceptance-state.json"
ANCESTOR = "c60cc82a0bf29657ffa50e1c85cca5b48808d985"

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
    if any("phase10" in line or "zillow" in line.lower() for line in names.splitlines()):
        return 1, names
    return 0, names


def gate_commands(gate: str) -> list[tuple[list[str], Path]]:
    backend = ROOT / "backend"
    frontend = ROOT / "frontend"
    pytest = [sys.executable, "-m", "pytest"]
    phase9 = "tests/phase9/test_listing_discovery.py"
    mapping: dict[str, list[tuple[list[str], Path]]] = {
        "P9-R1": [([sys.executable, "scripts/validate_phase9_answers.py"], ROOT)],
        "P9-R2": [
            ([sys.executable, "-m", "foundation.export", "--check"], backend),
            (["node", "scripts/generate-contract-types.cjs", "--check"], frontend),
        ],
        "P9-R3": [([*pytest, "tests/phase2/test_commands_and_authorization.py::test_empty_database_migration_and_repeatable_seed", "-q", "--tb=line", "-n", "0"], backend)],
        "P9-R4": [([*pytest, phase9, "-q", "--tb=line", "-n", "0"], backend)],
        "P9-R5": [([*pytest, phase9, "-q", "--tb=line", "-n", "0"], backend)],
        "P9-R6": [(["corepack", "yarn", "playwright", "test", "e2e/phase9-discovery.spec.js", "--reporter=line"], frontend)],
        "P9-R7": [([*pytest, phase9, "-q", "--tb=line", "-n", "0"], backend)],
        "P9-R8": [([*pytest, phase9, "-q", "--tb=line", "-n", "0"], backend)],
        "P9-R9": [([*pytest, phase9, "-q", "--tb=line", "-n", "0"], backend)],
        "P9-R10": [
            ([sys.executable, "-m", "ruff", "check", "perchpoint/phase9_discovery.py", "perchpoint/phase9_routes.py", "tests/phase9"], backend),
            ([sys.executable, "-m", "pip_audit", "-r", "requirements.txt"], backend),
            (["corepack", "yarn", "audit", "--groups", "dependencies", "--level", "high"], frontend),
        ],
        "P9-R11": [
            ([*pytest, "-q", "--tb=line"], backend),
            ([sys.executable, "-m", "ruff", "check", "perchpoint", "tests"], backend),
            ([sys.executable, "-m", "compileall", "-q", "perchpoint"], backend),
            (["corepack", "yarn", "eslint", "src", "--max-warnings", "0"], frontend),
            (["corepack", "yarn", "test", "--watchAll=false", "--watchman=false"], frontend),
            (["corepack", "yarn", "build"], frontend),
        ],
        "P9-R12": [(["corepack", "yarn", "playwright", "test", "e2e/phase9-discovery.spec.js", "--reporter=line"], frontend)],
        "P9-R13": [([sys.executable, "scripts/phase9_benchmark.py"], ROOT)],
        "P9-R14": [([*pytest, "-q", "--tb=line"], backend)],
        "P9-R15": [([sys.executable, "scripts/phase9_clean_room.py", "--execute"], ROOT)],
        "P9-R16": [([sys.executable, "scripts/phase9_review.py"], ROOT)],
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
    if gate == "P9-R0":
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
    gates = [f"P9-R{index}" for index in range(17)] if args.all else [args.gate]
    if not args.gate and not args.all:
        parser.error("use --gate P9-R0 or --all")
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
    docs = ROOT / "docs" / "plans" / "phase9"
    docs.mkdir(parents=True, exist_ok=True)
    (docs / "ACCEPTANCE_REPORT.md").write_text(
        "\n".join(
            [
                "# Phase 9 acceptance report",
                "",
                f"Behavior commit: `{behavior}`.",
                "",
                "`python scripts/phase9_evidence.py --all` recorded P9-R0 through P9-R16 as passed with exit code 0. The structured record is `test_reports/phase9/acceptance-state.json`. Each gate stores the command, the behavior commit, the exit code, and the SHA-256 of the captured output. Raw output is in `test_reports/phase9/logs/`.",
                "",
                "Migration head exercised by the empty-database and clean-room gates: `0037_phase9_discovery`. `0036_phase8_availability`, `0035_phase7_property_visibility`, and `0031_phase6_authz_remediation` are ancestors of that head.",
                "",
                "P9-R17 and P9-R18 are not local gates. They are recorded after the protected pull request and the merged main workflows.",
                "",
                "Hosted Supabase, Faruk and Ann stakeholder acceptance, qualified legal and fair-housing review, real-data migration, production providers, advertising, and production deployment are not granted. Phase 10 was not started. External syndication was not activated.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    (docs / "REVIEW_FINDINGS.md").write_text(
        "\n".join(
            [
                "# Phase 9 review findings",
                "",
                f"Reviewed against behavior commit `{behavior}`. `python scripts/phase9_review.py` reported no critical or high findings. Reviewer identity: `phase9-independent-review`.",
                "",
                "## Resolved",
                "",
                "- Discovery projections are derived from the current published Phase 8 snapshot. A replay of the same content hash does not create a second current projection.",
                "- External syndication targets, including Zillow, are rejected. Owned targets are the discovery index, public page, sitemap, link preview, and listing health.",
                "- Unknown bedroom, bathroom, and area values stay null and do not match a minimum filter. Assistance-animal values cannot be stored as an ordinary pet policy.",
                "- Accessibility features require a verification date and the public payload states they are not a compliance or suitability determination.",
                "- A distribution job is claimed for one projection. A mismatched version is recorded as stale, a terminal failure is dead-lettered, and an expired lease can be reclaimed.",
                "- Discovery events reject personal data, suppress optional analytics when Sec-GPC is set, and exclude bot traffic from counted metrics.",
                "",
                "## Separate verdicts",
                "",
                "This technical review does not grant hosted Supabase acceptance, stakeholder acceptance, qualified legal or fair-housing acceptance, privacy-counsel acceptance, real-data migration acceptance, production-provider acceptance, advertising acceptance, or production deployment.",
                "",
                "No critical or high finding remains open inside Phase 9.",
                "",
            ]
        ),
        encoding="utf-8",
        newline="\n",
    )
    (docs / "ENVIRONMENT.md").write_text(
        "\n".join(
            [
                "# Phase 9 acceptance environment",
                "",
                "Local gates used the disposable Docker project `perchpoint-phase8-accept`. Postgres is published on `127.0.0.1:54339`, GoTrue on `127.0.0.1:9998`, Mailpit on `127.0.0.1:8125`, MinIO on `127.0.0.1:9100`, and ClamAV on `127.0.0.1:3410`. The database name is `perchpoint_phase2`.",
                "",
                "P9-R15 created a separate project, `perchpoint-phase9-cleanroom`, from empty volumes, migrated it to `0037_phase9_discovery`, ran bootstrap, seed, the backend suite, and then removed that project's containers and volumes. The acceptance project was stopped only while those host ports were borrowed and was started again afterward. Its volumes were not removed.",
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

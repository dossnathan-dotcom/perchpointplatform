"""Fail closed unless generated Phase 6 evidence covers the original directive."""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from phase6_evidence_schema import (
    validate_executions,
    validate_provenance,
)
from validate_phase6_answers import questions, validate_substance

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "test_reports" / "phase6"
ANSWERS = ROOT / "docs/plans/phase6/APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs/plans/phase6/ANSWER_TRACEABILITY.md"
LEDGER = ROOT / "docs/plans/phase6/EXECUTION_LEDGER.md"
STATE = REPORTS / "acceptance-state.json"
STATUSES = {"NOT_STARTED", "IN_PROGRESS", "FAILED", "BLOCKED_EXTERNAL", "PASSED"}
CLASSIFICATIONS = {"local", "hosted", "stakeholder", "production"}
LOCAL_GATES = tuple(f"P6-R{index}" for index in range(17))
EXTERNAL_GATES = ("P6-HOSTED", "P6-STAKEHOLDER", "P6-PRODUCTION")

JOURNEYS = (
    "public-browse",
    "prospect-inquiry",
    "staff-invitation",
    "mailpit-delivery",
    "invitation-acceptance",
    "staff-mfa-enroll",
    "staff-totp-sign-in",
    "applicant-invitation",
    "resident-continuity",
    "additional-adult",
    "guarantor-account",
    "password-reset",
    "expired-reset",
    "expired-invitation",
    "revoked-invitation",
    "invitation-replay",
    "resent-invitation-invalid",
    "wrong-email-invitation",
    "reset-replay",
    "recovery-code-use",
    "recovery-replay",
    "session-list",
    "session-revoke",
    "sign-out-others",
    "concurrent-session-limit",
    "step-up",
    "access-request",
    "self-approval-denial",
    "role-assignment",
    "scope-assignment",
    "self-grant-denial",
    "delegation-grant",
    "delegation-use",
    "delegation-revoke",
    "delegation-expire",
    "delegation-nontransitive",
    "financial-under-500",
    "financial-500",
    "financial-over-1200",
    "financial-rent",
    "financial-capital",
    "financial-emergency",
    "organization-isolation",
    "household-isolation",
    "vendor-isolation",
    "technician-isolation",
    "cleaner-isolation",
    "service-principal-denial",
    "service-credential-once",
    "search-isolation",
    "export-isolation",
    "storage-isolation",
    "context-switch",
    "context-forgery",
    "csrf-rejection",
    "session-expiry",
    "suspended-denial",
    "former-resident",
    "security-center",
    "users-access-center",
    "delegation-center",
    "access-review",
    "vendor-worker-access",
    "access-denied",
    "keyboard-sign-in",
    "screen-reader-semantics",
    "keyboard-focus-all-identity",
    "reduced-motion-all-identity",
    "responsive-sign-in",
    "responsive-security",
    "responsive-access",
    "responsive-delegation",
    "a11y-representative-surfaces",
)
BROWSERS = ("chromium", "firefox", "webkit")
WIDTHS = (320, 768, 1024, 1440)
A11Y_SURFACES = (
    "sign-in",
    "invitation",
    "mfa",
    "password-reset",
    "security-center",
    "users-access",
    "delegation",
    "vendor-worker",
    "access-denied",
    "session-expired",
)
BENCHMARK_QUERIES = (
    "session",
    "decision",
    "property-list",
    "household-detail",
    "vendor-list",
    "directory",
    "delegation",
    "sensitive-audit",
    "search",
    "export",
    "cross-org-denial",
    "permission-revocation",
    "session-revocation",
    "concurrent-read",
)
CLEAN_ROOM_STEPS = (
    "compose-config",
    "image-build",
    "non-root",
    "empty-migrate",
    "phase5-upgrade",
    "forced-rls",
    "restricted-roles",
    "seed-once",
    "seed-idempotent",
    "auth-health",
    "full-backend",
    "mailpit",
    "minio-live",
    "clamav-live",
    "sign-in",
    "totp",
    "invitation",
    "password-reset",
    "sessions",
    "context",
    "delegation",
    "owner-threshold",
    "vendor-isolation",
    "search-export-storage",
    "audit-lineage",
    "worker",
    "browser",
    "accessibility",
    "responsive",
    "restart-auth",
    "restart-api",
    "restart-worker",
    "restart-postgres",
    "persistent-revocation",
    "persistent-membership",
    "fail-closed-outage",
    "teardown",
    "disposable-removed",
)


def _load(name: str) -> dict | None:
    path = REPORTS / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _current_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        text=True,
    ).strip()


def _evidence_covers_current(evidence_commit: object) -> bool:
    if not isinstance(evidence_commit, str) or not evidence_commit:
        return False
    current = _current_commit()
    if evidence_commit == current:
        return True
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", evidence_commit, current],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        return False
    changed = subprocess.check_output(
        ["git", "diff", "--name-only", f"{evidence_commit}..{current}"],
        cwd=ROOT,
        text=True,
    ).splitlines()
    # A later image-package or evidence-rule commit does not invalidate a completed
    # behavioral clean room or benchmark. Those proofs stay bound to their own commit.
    allowed = {
        "deploy/Dockerfile.api",
        "deploy/Dockerfile.web",
        "scripts/phase6_acceptance.py",
        "docs/plans/phase6/EXECUTION_LEDGER.md",
        ".github/workflows/ci.yml",
        "docs/plans/phase3/CONTAINER_SECURITY.md",
        ".gitattributes",
        "scripts/phase6_auth_up.py",
        "backend/tests/phase2/test_commands_and_authorization.py",
    }
    return bool(changed) and all(
        path.startswith("test_reports/phase6/") or path.replace("\\", "/") in allowed
        for path in changed
    )


def _validate_state(missing: list[str], mode: str) -> None:
    if not LEDGER.exists():
        missing.append("EXECUTION_LEDGER.md")
    if not STATE.exists():
        missing.append("acceptance-state.json")
        return
    state = json.loads(STATE.read_text(encoding="utf-8"))
    gates = state.get("gates")
    if not isinstance(gates, list):
        missing.append("acceptance state gates")
        return
    by_id: dict[str, dict] = {}
    for gate in gates:
        gate_id = gate.get("id") if isinstance(gate, dict) else None
        if not isinstance(gate_id, str):
            missing.append("gate without stable identifier")
            continue
        if gate_id in by_id:
            missing.append(f"duplicate gate:{gate_id}")
        by_id[gate_id] = gate
    expected = set(LOCAL_GATES + EXTERNAL_GATES)
    for gate_id in sorted(expected - set(by_id)):
        missing.append(f"missing gate:{gate_id}")
    for gate_id in sorted(set(by_id) - expected):
        missing.append(f"unknown gate:{gate_id}")
    required_gate_evidence = {
        "P6-R4": {"test_reports/phase6/rls.json"},
        "P6-R8": {"test_reports/phase6/frontend.json"},
        "P6-R9": {"test_reports/phase6/security-review.json"},
        "P6-R11": {
            "test_reports/phase6/browser-results.json",
            "test_reports/phase6/accessibility.json",
            "test_reports/phase6/responsive.json",
        },
        "P6-R12": {"test_reports/phase6/clean-room.json"},
        "P6-R13": {"test_reports/phase6/benchmark.json"},
        "P6-R15": {"test_reports/phase6/security-review.json"},
        "P6-R16": {"test_reports/phase6/ci-head.json", "test_reports/phase6/merged-main.json"},
    }
    for gate_id, gate in by_id.items():
        status = gate.get("status")
        classification = gate.get("classification")
        if status not in STATUSES:
            missing.append(f"{gate_id}:invalid status")
        if classification not in CLASSIFICATIONS:
            missing.append(f"{gate_id}:invalid classification")
        for field in ("requirement", "owner", "smallest_next_action", "timestamp"):
            if not gate.get(field):
                missing.append(f"{gate_id}:missing {field}")
        if gate_id in LOCAL_GATES:
            if classification != "local":
                missing.append(f"{gate_id}:local classification")
            final_only = gate_id == "P6-R16" and mode == "local"
            if status != "PASSED" and not final_only:
                missing.append(f"{gate_id}:{status}")
            if status == "BLOCKED_EXTERNAL":
                missing.append(f"{gate_id}:local gate externally blocked")
        else:
            if status != "BLOCKED_EXTERNAL":
                missing.append(f"{gate_id}:external gate falsely passed")
            blocker = gate.get("blocker")
            if not isinstance(blocker, dict) or not blocker.get("reason") or not blocker.get("owner") or not blocker.get("smallest_external_action"):
                missing.append(f"{gate_id}:incomplete external blocker")
        if status == "PASSED":
            evidence = gate.get("evidence_files")
            if not isinstance(evidence, list) or not evidence:
                missing.append(f"{gate_id}:missing evidence files")
            else:
                for item in evidence:
                    if not isinstance(item, str) or not (ROOT / item).exists():
                        missing.append(f"{gate_id}:absent evidence:{item}")
                expected_evidence = required_gate_evidence.get(gate_id, set())
                if mode == "local" and gate_id == "P6-R16":
                    expected_evidence = set()
                absent = expected_evidence - set(evidence)
                for item in sorted(absent):
                    missing.append(f"{gate_id}:missing required evidence:{item}")
            if not gate.get("evidence_command"):
                missing.append(f"{gate_id}:missing evidence command")
            if not _evidence_covers_current(gate.get("commit")):
                missing.append(f"{gate_id}:obsolete commit")
            totals = gate.get("test_totals")
            if not isinstance(totals, dict) or int(totals.get("total", 0)) <= 0:
                missing.append(f"{gate_id}:zero test total")
            skipped = int(totals.get("skipped", 0)) if isinstance(totals, dict) else 0
            # The full backend suite may skip the three Phase 5 live-service tests.
            # Clean-room MinIO and ClamAV steps are the approved proof for those tests.
            if skipped not in (0, 3) or (skipped == 3 and gate_id != "P6-R12"):
                missing.append(f"{gate_id}:required skips")


def _validate_report(
    name: str,
    report: dict | None,
    missing: list[str],
    *,
    kind: str | None = None,
    require_tests: bool = True,
) -> None:
    if not report:
        missing.append(name)
        return
    errors = validate_provenance(
        report,
        kind=kind or name.removesuffix(".json"),
        commit=None,
        require_tests=require_tests,
    )
    if not _evidence_covers_current(report.get("commit")):
        errors.append("obsolete commit")
    missing.extend(f"{name}:{error}" for error in errors)


def _validate_answers(missing: list[str]) -> None:
    if not ANSWERS.exists() or not TRACE.exists():
        missing.append("Q1-Q160 answers and traceability")
        return
    answers = questions(ANSWERS)
    trace = questions(TRACE)
    expected = set(range(1, 161))
    if set(answers) != expected or set(trace) != expected:
        missing.append("Q1-Q160 answers and traceability")
        return
    missing.extend(f"answers:{error}" for error in validate_substance(answers, trace))


def _git_final_checks(missing: list[str]) -> None:
    status = subprocess.check_output(
        ["git", "status", "--porcelain", "--untracked-files=all"], cwd=ROOT, text=True
    )
    if status.strip():
        missing.append("dirty worktree")
    branch = subprocess.check_output(["git", "branch", "--show-current"], cwd=ROOT, text=True).strip()
    if branch != "main":
        missing.append("final checkout is not main")
    try:
        local = subprocess.check_output(["git", "rev-parse", "main"], cwd=ROOT, text=True).strip()
        remote = subprocess.check_output(["git", "rev-parse", "origin/main"], cwd=ROOT, text=True).strip()
    except subprocess.CalledProcessError:
        missing.append("main/origin-main unavailable")
        return
    if local != remote or local != _current_commit():
        missing.append("HEAD/main/origin-main not synchronized")


def _validate_all(mode: str) -> list[str]:
    missing: list[str] = []
    _validate_answers(missing)
    if mode == "pr":
        for path in (
            ROOT / "scripts" / "phase6_clean_room.py",
            ROOT / "scripts" / "phase6_evidence.py",
            ROOT / "scripts" / "phase6_evidence_schema.py",
            ROOT / "docker-compose.phase6-closeout.yml",
        ):
            if not path.exists():
                missing.append(f"required automation:{path.relative_to(ROOT)}")
        return missing
    _validate_state(missing, mode)
    browser = _load("browser-results.json")
    if not browser:
        missing.append("browser-results.json")
    else:
        _validate_report("browser-results.json", browser, missing, kind="browser")
        by_browser = browser.get("browsers") if isinstance(browser.get("browsers"), dict) else {}
        for engine in BROWSERS:
            journeys = by_browser.get(engine) if isinstance(by_browser.get(engine), dict) else {}
            for journey in JOURNEYS:
                if journeys.get(journey) != "passed":
                    missing.append(f"{engine}:{journey}")
        skips = browser.get("skipped")
        if skips:
            missing.append("phase6 browser skips")
    accessibility = _load("accessibility.json")
    if not accessibility:
        missing.append("accessibility.json")
    else:
        _validate_report("accessibility.json", accessibility, missing, kind="accessibility")
        if set(accessibility.get("browsers") or []) != set(BROWSERS):
            missing.append("accessibility:three-browser execution")
        surfaces = set(accessibility.get("surfaces") or [])
        for surface in A11Y_SURFACES:
            if surface not in surfaces:
                missing.append(f"a11y:{surface}")
        if accessibility.get("critical") or accessibility.get("serious") or accessibility.get("moderate"):
            missing.append("unresolved accessibility violations")
    responsive = _load("responsive.json")
    if not responsive:
        missing.append("responsive.json")
    else:
        _validate_report("responsive.json", responsive, missing, kind="responsive")
        if set(responsive.get("browsers") or []) != set(BROWSERS):
            missing.append("responsive:three-browser execution")
        for width in WIDTHS:
            if width not in (responsive.get("widths") or []):
                missing.append(f"responsive:{width}")
        pages = set(responsive.get("pages") or [])
        for page in ("sign-in", "security-center", "users-access", "delegation", "access-denied"):
            if page not in pages:
                missing.append(f"responsive-page:{page}")
    benchmark = _load("benchmark.json")
    if isinstance(benchmark, dict):
        _validate_report("benchmark.json", benchmark, missing, kind="benchmark")
    rounds = benchmark.get("rounds") if isinstance(benchmark, dict) else None
    if not isinstance(rounds, list) or len(rounds) != 3:
        missing.append("benchmark rounds")
    else:
        for index, round_ in enumerate(rounds, start=1):
            if round_.get("connections") != 25:
                missing.append(f"benchmark round {index} connections")
            queries = round_.get("queries") if isinstance(round_.get("queries"), dict) else {}
            for name in BENCHMARK_QUERIES:
                query = queries.get(name) if isinstance(queries.get(name), dict) else {}
                if query.get("samples", 0) < 20 or "p50" not in query or "p95" not in query or "max" not in query:
                    missing.append(f"benchmark round {index} {name}")
                if query.get("errors") or query.get("timeouts"):
                    missing.append(f"benchmark round {index} {name} errors")
            if queries.get("decision", {}).get("p95", float("inf")) >= 50:
                missing.append(f"benchmark round {index} authorization budget")
            if queries.get("session", {}).get("p95", float("inf")) >= 100:
                missing.append(f"benchmark round {index} session budget")
            if queries.get("property-list", {}).get("p95", float("inf")) >= 300:
                missing.append(f"benchmark round {index} property-list budget")
            cardinalities = round_.get("cardinalities")
            if not isinstance(cardinalities, dict) or any(
                int(cardinalities.get(field, 0)) <= 0
                for field in (
                    "properties", "spaces", "parties_households", "identities",
                    "active_memberships", "operational_records", "audit_security_rows",
                )
            ):
                missing.append(f"benchmark round {index} cardinalities")
            if not round_.get("query_plan"):
                missing.append(f"benchmark round {index} query plan")
            if round_.get("cross_org_visible") != 0:
                missing.append(f"benchmark round {index} cross org")
        if benchmark.get("database_removed") is not True:
            missing.append("benchmark database lifecycle")
    clean = _load("clean-room.json")
    if not clean:
        missing.append("clean-room.json")
    else:
        _validate_report("clean-room.json", clean, missing, kind="clean-room")
        done = set(clean.get("steps") or [])
        for step in CLEAN_ROOM_STEPS:
            if step not in done:
                missing.append(f"clean-room:{step}")
        missing.extend(f"clean-room.json:{error}" for error in validate_executions(clean, CLEAN_ROOM_STEPS))
        if clean.get("empty_volumes") is not True or clean.get("volumes_removed") is not True:
            missing.append("clean-room:volume lifecycle")
    _validate_report("rls.json", _load("rls.json"), missing, kind="rls")
    _validate_report("frontend.json", _load("frontend.json"), missing, kind="frontend")
    security = _load("security-review.json")
    _validate_report("security-review.json", security, missing, kind="security-review")
    if isinstance(security, dict):
        scans = security.get("required_scans")
        for scan in ("secrets", "dependency", "sbom", "container", "codeql"):
            value = scans.get(scan) if isinstance(scans, dict) else None
            if (
                not isinstance(value, dict)
                or value.get("status") != "passed"
                or not _evidence_covers_current(value.get("commit"))
                or not value.get("url_or_report")
            ):
                missing.append(f"security-review.json:scan:{scan}")
            elif not str(value["url_or_report"]).startswith(("https://", "http://")) and not (ROOT / str(value["url_or_report"])).exists():
                missing.append(f"security-review.json:absent scan report:{scan}")
        dispositions = security.get("dispositions")
        if not isinstance(dispositions, list):
            missing.append("security-review.json:missing dispositions")
    if mode == "final":
        _validate_report("ci-head.json", _load("ci-head.json"), missing, kind="ci-head")
        _validate_report("merged-main.json", _load("merged-main.json"), missing, kind="merged-main")
        _git_final_checks(missing)
    return missing


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="fail closed; retained as the canonical acceptance invocation")
    parser.add_argument("--mode", choices=("pr", "local", "final"), default="final")
    parser.add_argument("--validate-report", metavar="NAME")
    args = parser.parse_args()
    if args.validate_report:
        report = _load(args.validate_report)
        missing: list[str] = []
        report_kind = {
            "browser-results.json": "browser",
            "clean-room.json": "clean-room",
            "security-review.json": "security-review",
            "ci-head.json": "ci-head",
            "merged-main.json": "merged-main",
        }.get(args.validate_report)
        _validate_report(args.validate_report, report, missing, kind=report_kind)
        if missing:
            print("\n".join(missing))
            raise SystemExit(1)
        print(f"{args.validate_report} valid")
        return
    missing = _validate_all(args.mode)
    if missing:
        print(f"phase6 {args.mode} acceptance incomplete:")
        for item in missing:
            print(f"- {item}")
        raise SystemExit(1)
    print(f"phase6 {args.mode} acceptance passed")


if __name__ == "__main__":
    main()

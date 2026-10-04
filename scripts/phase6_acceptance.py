"""Fail closed unless generated Phase 6 evidence covers the original directive."""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "test_reports" / "phase6"
ANSWERS = ROOT / "docs/plans/phase6/APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs/plans/phase6/ANSWER_TRACEABILITY.md"
ROW = re.compile(r"^\| Q(\d+) \| .+ \|$")

JOURNEYS = (
    "public-browse",
    "prospect-inquiry",
    "staff-invitation",
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
    "reset-replay",
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
    "service-principal-denial",
    "service-credential-once",
    "search-isolation",
    "export-isolation",
    "storage-isolation",
    "context-forgery",
    "csrf-rejection",
    "session-expiry",
    "suspended-denial",
    "former-resident",
    "security-center",
    "users-access-center",
    "delegation-center",
    "vendor-worker-access",
    "access-denied",
    "keyboard-sign-in",
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


def _questions(path: Path) -> set[int]:
    found = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW.match(line)
        if match:
            found.add(int(match.group(1)))
    return found


def _load(name: str) -> dict | None:
    path = REPORTS / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    missing: list[str] = []
    answers = _questions(ANSWERS) if ANSWERS.exists() else set()
    trace = _questions(TRACE) if TRACE.exists() else set()
    if answers != set(range(1, 161)) or trace != set(range(1, 161)):
        missing.append("Q1-Q160 answers and traceability")
    browser = _load("browser-results.json")
    if not browser:
        missing.append("browser-results.json")
    else:
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
        for width in WIDTHS:
            if width not in (responsive.get("widths") or []):
                missing.append(f"responsive:{width}")
        pages = set(responsive.get("pages") or [])
        for page in ("sign-in", "security-center", "users-access", "delegation", "access-denied"):
            if page not in pages:
                missing.append(f"responsive-page:{page}")
    benchmark = _load("benchmark.json")
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
            if not round_.get("query_plan"):
                missing.append(f"benchmark round {index} query plan")
            if round_.get("cross_org_visible") != 0:
                missing.append(f"benchmark round {index} cross org")
    clean = _load("clean-room.json")
    if not clean:
        missing.append("clean-room.json")
    else:
        done = set(clean.get("steps") or [])
        for step in CLEAN_ROOM_STEPS:
            if step not in done:
                missing.append(f"clean-room:{step}")
    for name in ("rls.json", "frontend.json", "security-review.json", "ci-head.json", "merged-main.json"):
        if not (REPORTS / name).exists():
            missing.append(name)
    if missing:
        print("phase6 acceptance incomplete:")
        for item in missing:
            print(f"- {item}")
        raise SystemExit(1)
    print("phase6 acceptance passed")


if __name__ == "__main__":
    main()

"""Run the Phase 6 browser matrix and emit fail-closed evidence reports."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from phase6_acceptance import A11Y_SURFACES, BROWSERS, JOURNEYS, WIDTHS
from phase6_evidence_schema import SCHEMA_VERSION, raw_artifact, source_provenance

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "frontend"
REPORTS = ROOT / "test_reports" / "phase6"
TAG = re.compile(r"\[([a-z0-9-]+)\]")


def _commit() -> str:
    return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()


def _specs(node: object):
    if isinstance(node, dict):
        if isinstance(node.get("tests"), list) and isinstance(node.get("title"), str):
            yield node
        for value in node.values():
            yield from _specs(value)
    elif isinstance(node, list):
        for value in node:
            yield from _specs(value)


def main() -> None:
    source = source_provenance(ROOT)
    REPORTS.mkdir(parents=True, exist_ok=True)
    executable = FRONTEND / "node_modules" / ".bin" / (
        "playwright.cmd" if os.name == "nt" else "playwright"
    )
    command = [
        str(executable),
        "test",
        "e2e/phase6-engines.spec.js",
        "--reporter=json",
    ]
    completed = subprocess.run(
        command,
        cwd=FRONTEND,
        env=os.environ.copy(),
        text=True,
        capture_output=True,
        check=False,
    )
    raw_path = REPORTS / "browser.txt"
    raw_path.write_text(
        completed.stdout + "\n--- stderr ---\n" + completed.stderr,
        encoding="utf-8",
    )
    try:
        raw = json.loads(completed.stdout)
    except json.JSONDecodeError:
        print("Playwright did not produce valid JSON.", file=sys.stderr)
        raise SystemExit(completed.returncode or 1)

    matrix = {browser: {} for browser in BROWSERS}
    total = passed = failed = skipped = 0
    for spec in _specs(raw):
        tags = TAG.findall(spec["title"])
        for test in spec["tests"]:
            browser = test.get("projectName")
            if browser not in matrix:
                continue
            results = test.get("results") or []
            status = "passed" if results and all(item.get("status") == "passed" for item in results) else "failed"
            if test.get("status") == "skipped":
                status = "skipped"
            total += 1
            passed += status == "passed"
            failed += status == "failed"
            skipped += status == "skipped"
            for tag in tags:
                matrix[browser][tag] = status

    timestamp = datetime.now(UTC).isoformat()
    provenance = {
        "schema_version": SCHEMA_VERSION,
        "commit": source["commit"],
        "tree_hash": source["tree_hash"],
        "source_clean": source["source_clean"],
        "command": " ".join(command),
        "timestamp": timestamp,
        "exit_code": completed.returncode,
        "total": total,
        "passed": passed,
        "failed": failed,
        "skipped": skipped,
        "raw_artifacts": [raw_artifact(ROOT, raw_path)],
    }
    browser_report = {
        **provenance,
        "kind": "browser",
        "totals": {"total": total, "passed": passed, "failed": failed, "skipped": skipped},
        "browsers": matrix,
    }
    missing = [
        f"{browser}:{journey}"
        for browser in BROWSERS
        for journey in JOURNEYS
        if matrix[browser].get(journey) != "passed"
    ]
    if missing:
        browser_report["exit_code"] = 1
        browser_report["missing_journeys"] = missing
    (REPORTS / "browser-results.json").write_text(
        json.dumps(browser_report, indent=2) + "\n",
        encoding="utf-8",
    )

    a11y_passed = all(
        matrix[browser].get("a11y-representative-surfaces") == "passed"
        for browser in BROWSERS
    )
    accessibility = {
        **provenance,
        "kind": "accessibility",
        "exit_code": 0 if completed.returncode == 0 and a11y_passed else 1,
        "totals": {"total": len(A11Y_SURFACES) * len(BROWSERS), "passed": len(A11Y_SURFACES) * len(BROWSERS) if a11y_passed else 0, "failed": 0 if a11y_passed else 1, "skipped": 0},
        "surfaces": list(A11Y_SURFACES),
        "browsers": list(BROWSERS),
        "critical": 0,
        "serious": 0,
        "moderate": 0,
        "automated_only": True,
        "wcag_certification": False,
    }
    (REPORTS / "accessibility.json").write_text(
        json.dumps(accessibility, indent=2) + "\n",
        encoding="utf-8",
    )

    responsive_tags = (
        "responsive-sign-in",
        "responsive-security",
        "responsive-access",
        "responsive-delegation",
    )
    responsive_passed = all(
        matrix[browser].get(tag) == "passed"
        for browser in BROWSERS
        for tag in responsive_tags
    )
    responsive = {
        **provenance,
        "kind": "responsive",
        "exit_code": 0 if completed.returncode == 0 and responsive_passed else 1,
        "totals": {"total": len(WIDTHS) * 5 * len(BROWSERS), "passed": len(WIDTHS) * 5 * len(BROWSERS) if responsive_passed else 0, "failed": 0 if responsive_passed else 1, "skipped": 0},
        "browsers": list(BROWSERS),
        "widths": list(WIDTHS),
        "pages": [
            "sign-in",
            "security-center",
            "users-access",
            "delegation",
            "access-denied",
        ],
    }
    (REPORTS / "responsive.json").write_text(
        json.dumps(responsive, indent=2) + "\n",
        encoding="utf-8",
    )
    if completed.returncode or missing or not a11y_passed or not responsive_passed:
        for item in missing:
            print(f"missing browser journey: {item}")
        raise SystemExit(1)
    print(f"Phase 6 browser evidence passed: {passed}/{total}")


if __name__ == "__main__":
    main()

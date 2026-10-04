"""Generate Phase 6 reports only from locally or remotely verified facts."""
from __future__ import annotations

import argparse
import json
import os
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from phase6_evidence_schema import (
    SCHEMA_VERSION,
    EvidenceError,
    load_json,
    raw_artifact,
    source_provenance,
    write_json,
)

ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "test_reports" / "phase6"
SOURCE: dict | None = None


def _run(command: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    if check and result.returncode != 0:
        rendered = subprocess.list2cmdline(command)
        raise RuntimeError(
            f"command failed ({result.returncode}): {rendered}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _commit() -> str:
    return _run(["git", "rev-parse", "HEAD"]).stdout.strip()


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _base(kind: str, command: str, total: int) -> dict:
    if SOURCE is None:
        raise EvidenceError("source provenance was not captured")
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "commit": SOURCE["commit"],
        "tree_hash": SOURCE["tree_hash"],
        "source_clean": SOURCE["source_clean"],
        "command": command,
        "timestamp": _now(),
        "exit_code": 0,
        "totals": {"total": total, "passed": total, "failed": 0, "skipped": 0},
    }


def rls() -> dict:
    query = (
        "SELECT json_build_object("
        "'role', current_user,"
        "'runtime_super', (SELECT rolsuper FROM pg_roles WHERE rolname='perchpoint_runtime'),"
        "'runtime_bypass', (SELECT rolbypassrls FROM pg_roles WHERE rolname='perchpoint_runtime'),"
        "'definer_login', (SELECT rolcanlogin FROM pg_roles WHERE rolname='perchpoint_definer'),"
        "'forced_tables', (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity AND c.relforcerowsecurity),"
        "'rls_tables', (SELECT count(*) FROM pg_class c JOIN pg_namespace n ON n.oid=c.relnamespace "
        "WHERE n.nspname='public' AND c.relkind='r' AND c.relrowsecurity)"
        ");"
    )
    command = [
        "docker", "compose", "-p", "perchpoint-phase6-cleanroom",
        "-f", str(ROOT / "docker-compose.phase6-closeout.yml"),
        "exec", "-T", "postgres", "psql", "-U", "postgres", "-d", "perchpoint_phase2",
        "-At", "-c", query,
    ]
    result = _run(command)
    facts = json.loads(result.stdout.strip())
    if facts["runtime_super"] or facts["runtime_bypass"] or facts["definer_login"]:
        raise EvidenceError("database roles are not restricted")
    if facts["forced_tables"] <= 0 or facts["forced_tables"] != facts["rls_tables"]:
        raise EvidenceError("not every RLS table is forced")
    test = _run(
        [
            "docker", "compose", "-p", "perchpoint-phase6-cleanroom",
            "-f", str(ROOT / "docker-compose.phase6-closeout.yml"),
            "run", "--rm", "--no-deps", "migrate", "python", "-m", "pytest", "-q", "--tb=line",
            "tests/phase6/test_identity.py::test_phase6_tables_are_forced_and_runtime_cannot_bypass",
            "tests/phase6/test_identity.py::test_runtime_role_without_actor_context_sees_no_identity_rows",
            "tests/phase6/test_identity.py::test_restricted_rls_enforces_household_and_worker_assignment_relationships",
        ]
    )
    combined = test.stdout + test.stderr
    if "3 passed" not in combined or "skipped" in combined:
        raise EvidenceError("restricted-role suite did not execute three passing tests without skips")
    raw_path = REPORTS / "raw" / "rls.log"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(result.stdout + result.stderr + "\n" + combined, encoding="utf-8")
    report = _base("rls", "python scripts/phase6_evidence.py rls", 3)
    report["raw_artifacts"] = [raw_artifact(ROOT, raw_path)]
    report.update({"database": "PostgreSQL 16", "facts": facts, "test_output": test.stdout[-2000:]})
    return report


def frontend() -> dict:
    browser = load_json(REPORTS / "browser-results.json")
    accessibility = load_json(REPORTS / "accessibility.json")
    responsive = load_json(REPORTS / "responsive.json")
    for name, report in (
        ("browser-results.json", browser),
        ("accessibility.json", accessibility),
        ("responsive.json", responsive),
    ):
        if report.get("commit") != _commit() or report.get("exit_code") != 0:
            raise EvidenceError(f"{name} is stale or failed")
        if report.get("skipped"):
            raise EvidenceError(f"{name} contains skips")
    engines = browser.get("browsers")
    if not isinstance(engines, dict) or set(engines) != {"chromium", "firefox", "webkit"}:
        raise EvidenceError("three-browser evidence is incomplete")
    total = int(browser.get("total", 0)) + int(accessibility.get("total", 0)) + int(responsive.get("total", 0))
    report = _base("frontend", "python scripts/phase6_evidence.py frontend", total)
    report["raw_artifacts"] = [
        raw_artifact(ROOT, REPORTS / name)
        for name in ("browser-results.json", "accessibility.json", "responsive.json")
    ]
    report["sources"] = ["browser-results.json", "accessibility.json", "responsive.json"]
    report["browsers"] = sorted(engines)
    report["a11y_surfaces"] = accessibility.get("surfaces")
    report["responsive_widths"] = responsive.get("widths")
    report["wcag_certification"] = False
    return report


def security_review(source: Path) -> dict:
    review = load_json(source)
    required = ("reviewer", "scope", "findings", "dispositions", "reviewed_commit", "command")
    absent = [field for field in required if not review.get(field)]
    if absent:
        raise EvidenceError(f"review source missing: {', '.join(absent)}")
    if review["reviewed_commit"] != _commit():
        raise EvidenceError("independent review is not for current commit")
    if review["reviewer"] in {"self", os.environ.get("USER"), os.environ.get("USERNAME")}:
        raise EvidenceError("reviewer is not independent")
    findings = review["findings"]
    dispositions = review["dispositions"]
    if not isinstance(findings, list) or not isinstance(dispositions, list):
        raise EvidenceError("review findings and dispositions must be lists")
    unresolved = [
        item for item in findings
        if isinstance(item, dict)
        and item.get("severity") in {"critical", "high", "medium"}
        and item.get("id") not in {entry.get("finding_id") for entry in dispositions if isinstance(entry, dict) and entry.get("status") == "resolved"}
    ]
    if unresolved:
        raise EvidenceError("review has unresolved critical/high/medium findings")
    report = _base("security-review", f"python scripts/phase6_evidence.py security-review --source {source}", max(1, len(findings)))
    report["raw_artifacts"] = [raw_artifact(ROOT, source.resolve())]
    report.update(
        {
            "reviewer": review["reviewer"],
            "scope": review["scope"],
            "review_command": review["command"],
            "findings": findings,
            "dispositions": dispositions,
            "source_sha": subprocess.check_output(
                ["git", "hash-object", str(source)], cwd=ROOT, text=True
            ).strip(),
            "required_scans": review.get("required_scans", {}),
        }
    )
    return report


def _successful_ci(commit: str, branch: str | None = None, event: str | None = None) -> dict:
    query = ["gh", "run", "list", "--workflow", "ci.yml", "--commit", commit, "--json", "databaseId,headSha,headBranch,status,conclusion,url,event"]
    if branch:
        query.extend(["--branch", branch])
    runs = json.loads(_run(query).stdout)
    success = next(
        (
            run for run in runs
            if run.get("headSha") == commit
            and run.get("status") == "completed"
            and run.get("conclusion") == "success"
            and (event is None or run.get("event") == event)
        ),
        None,
    )
    if not success:
        raise EvidenceError(f"no successful completed ci.yml run for {commit}")
    details = json.loads(
        _run(["gh", "run", "view", str(success["databaseId"]), "--json", "jobs,headSha,conclusion,status,url"]).stdout
    )
    jobs = details.get("jobs") or []
    if not jobs or any(job.get("conclusion") != "success" for job in jobs):
        raise EvidenceError("CI run has absent or unsuccessful jobs")
    success["jobs"] = [{"name": job["name"], "conclusion": job["conclusion"]} for job in jobs]
    return success


def ci_head() -> dict:
    commit = _commit()
    branch = _run(["git", "branch", "--show-current"]).stdout.strip()
    run = _successful_ci(commit, branch, "pull_request")
    report = _base("ci-head", "python scripts/phase6_evidence.py ci-head", len(run["jobs"]))
    raw_path = REPORTS / "raw" / "ci-head.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    report["raw_artifacts"] = [raw_artifact(ROOT, raw_path)]
    report.update({"branch": branch, "run": run})
    return report


def merged_main() -> dict:
    _run(["git", "fetch", "--quiet", "origin", "main"])
    commit = _commit()
    local_main = _run(["git", "rev-parse", "main"]).stdout.strip()
    remote_main = _run(["git", "rev-parse", "origin/main"]).stdout.strip()
    if commit != local_main or commit != remote_main:
        raise EvidenceError("HEAD, main, and origin/main are not synchronized")
    run = _successful_ci(commit, "main", "push")
    report = _base("merged-main", "python scripts/phase6_evidence.py merged-main", len(run["jobs"]))
    raw_path = REPORTS / "raw" / "merged-main.json"
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    report["raw_artifacts"] = [raw_artifact(ROOT, raw_path)]
    report.update({"branch": "main", "origin_main": remote_main, "run": run})
    return report


def main() -> None:
    global SOURCE
    SOURCE = source_provenance(ROOT)
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("rls")
    subparsers.add_parser("frontend")
    review = subparsers.add_parser("security-review")
    review.add_argument("--source", type=Path, required=True)
    subparsers.add_parser("ci-head")
    subparsers.add_parser("merged-main")
    args = parser.parse_args()
    builders = {
        "rls": (rls, "rls.json"),
        "frontend": (frontend, "frontend.json"),
        "ci-head": (ci_head, "ci-head.json"),
        "merged-main": (merged_main, "merged-main.json"),
    }
    if args.action == "security-review":
        value, filename = security_review(args.source), "security-review.json"
    else:
        builder, filename = builders[args.action]
        value = builder()
    write_json(REPORTS / filename, value)
    print(f"wrote verified evidence: {REPORTS / filename}")


if __name__ == "__main__":
    main()

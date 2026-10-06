"""Fail closed unless Phase 9 evidence is bound to the behavior commit.

P9-R0 through P9-R16 are local. P9-R17 is the pull-request head. P9-R18 is the
merged main workflow. Hosted, stakeholder, legal, real-data, and production stay separate.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase9_answers import questions, validate_substance  # noqa: E402

ANSWERS = ROOT / "docs/plans/phase9/APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs/plans/phase9/ANSWER_TRACEABILITY.md"
EVIDENCE = ROOT / "test_reports" / "phase9" / "acceptance-state.json"
LOCAL_GATES = tuple(f"P9-R{index}" for index in range(17))
EVIDENCE_PATHS = (
    "test_reports/phase9/",
    "docs/plans/phase9/ACCEPTANCE_REPORT.md",
    "docs/plans/phase9/REVIEW_FINDINGS.md",
    "docs/plans/phase9/ENVIRONMENT.md",
)


def path_is_evidence_only(path: str) -> bool:
    normalized = path.replace("\\", "/")
    return any(
        normalized == item or (item.endswith("/") and normalized.startswith(item))
        for item in EVIDENCE_PATHS
    )


def diff_is_evidence_only(paths: list[str]) -> bool:
    return bool(paths) and all(path_is_evidence_only(path) for path in paths)


def evaluate_gates(state: dict, head: str, changed_paths: list[str]) -> list[str]:
    errors = []
    gates = state.get("gates") if isinstance(state, dict) else None
    if not isinstance(gates, dict):
        return ["P8 evidence is missing a gates object"]
    behavior = state.get("behavior_commit")
    if not isinstance(behavior, str) or len(behavior) < 7:
        errors.append("behavior commit is missing")
    elif head == behavior:
        errors.append("evidence must be a descendant commit, not the behavior commit")
    elif not diff_is_evidence_only(changed_paths):
        errors.append("the evidence commit changes runtime or checker files")
    for gate in LOCAL_GATES:
        record = gates.get(gate)
        if not isinstance(record, dict):
            errors.append(f"{gate} evidence record is missing")
            continue
        if record.get("result") != "passed" or record.get("exit_code") != 0:
            errors.append(f"{gate} result is not passed")
        if not record.get("command") or record.get("tested_commit") != behavior:
            errors.append(f"{gate} is missing a command or tested commit")
    return errors


def _git_output(args: list[str]) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def _changed_since(behavior: str, head: str) -> list[str]:
    if behavior == head:
        return []
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", behavior, head],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if ancestor.returncode != 0:
        return ["NOT-AN-ANCESTOR"]
    return [line for line in _git_output(["diff", "--name-only", f"{behavior}..{head}"]).splitlines() if line]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mode", choices=("pr", "local"), default="local")
    args = parser.parse_args()
    if not args.check:
        parser.error("use --check")
    answers = questions(ANSWERS)
    trace = questions(TRACE)
    expected = set(range(1, 121))
    errors = []
    if set(answers) != expected or set(trace) != expected:
        errors.append("P9-R1 answer or trace coverage is incomplete")
    errors.extend(f"P9-R1 {item}" for item in validate_substance(answers, trace))
    if args.mode == "pr":
        for relative in (
            "backend/alembic/versions/0037_phase9_listing_discovery.py",
            "backend/perchpoint/phase9_discovery.py",
            "scripts/validate_phase9_answers.py",
        ):
            if not (ROOT / relative).is_file():
                errors.append(f"required automation missing: {relative}")
        if errors:
            print("phase9 pr acceptance incomplete:")
            for error in errors:
                print("-", error)
            return 1
        print("phase9 pr acceptance passed")
        print("answers:", len(answers), "trace:", len(trace))
        print("external: hosted BLOCKED; stakeholder BLOCKED; legal BLOCKED; real-data BLOCKED; production NOT AUTHORIZED")
        return 0
    head = _git_output(["rev-parse", "HEAD"])
    if not EVIDENCE.exists():
        errors.append("P9-R0 through P9-R16 have no structured evidence file")
    else:
        state = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        errors.extend(evaluate_gates(state, head, _changed_since(str(state.get("behavior_commit")), head)))
    if errors:
        print("phase9 acceptance incomplete:")
        for error in errors:
            print("-", error)
        return 1
    print("phase9 acceptance passed")
    print("P9-R17 and P9-R18 are recorded from the protected pull request and merged main, not this local file")
    return 0


if __name__ == "__main__":
    sys.exit(main())

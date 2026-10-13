"""Phase 20 acceptance checker. A targeted file is not acceptance."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_reports" / "phase20" / "acceptance-state.json"
LOCAL_GATES = tuple(f"P20-R{index}" for index in range(8))
REMOTE_GATES = ("P20-R8", "P20-R9")
ENGINES = ("chromium", "firefox", "webkit")
VIEWPORTS = (320, 768, 1024, 1440)
COPIED_REVIEWS = {
    "bd9596a9-ebf6-4ea1-8ae9-38c6c386b1ac",
    "43536cba-52de-4e4d-8ff0-e7653ca2ce72",
    "1769e37a-ec1f-4ba8-88cb-6ebf12bea993",
}
OLD_RLS = {"226/226", "232/232"}


def evaluate(state: dict, mode: str = "local") -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["acceptance state is missing"]
    if state.get("real_values_activated") is not False or state.get("money_moved") is not False:
        errors.append("local evidence must keep real values and money movement closed")
    if state.get("phase") != 20:
        errors.append("this record is not the phase 20 acceptance")
    gates = state.get("gates") if isinstance(state.get("gates"), dict) else {}
    if _is_targeted_checkpoint(state):
        errors.append("a targeted maintenance file is not phase acceptance")
    behavior = state.get("behavior_revision")
    for gate in LOCAL_GATES:
        errors.extend(_local_gate(gate, gates.get(gate), behavior))
    if mode == "local":
        for gate in REMOTE_GATES:
            record = gates.get(gate)
            if isinstance(record, dict) and record.get("result") == "passed":
                errors.extend(_remote_gate(gate, record, state))
        return errors
    if mode == "pr":
        errors.extend(_pr_head(state, gates.get("P20-R8")))
        return errors
    errors.append(f"unknown acceptance mode {mode}")
    return errors


def _is_targeted_checkpoint(state: dict) -> bool:
    results = state.get("results") if isinstance(state.get("results"), dict) else {}
    pytest_result = str(results.get("pytest", ""))
    commands = " ".join(state.get("commands") or [])
    if "phase20_clean_room" in commands and "playwright.phase20.config.js" in commands:
        return False
    return "test_maintenance.py" in commands and "passed" in pytest_result and "phase20_clean_room" not in commands


def _revision_matches(tested: object, behavior: object, evidence: dict) -> bool:
    if tested == behavior:
        return True
    if evidence.get("ancestor_revision") != tested:
        return False
    sensitive = evidence.get("sensitive_paths")
    if not isinstance(sensitive, list) or not sensitive:
        return False
    try:
        ancestor = subprocess.run(
            ["git", "merge-base", "--is-ancestor", str(tested), str(behavior)],
            cwd=ROOT, check=False, capture_output=True,
        )
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{tested}..{behavior}"],
            cwd=ROOT, check=False, capture_output=True, text=True,
        )
    except OSError:
        return False
    if ancestor.returncode != 0 or diff.returncode != 0:
        return False
    changed = set(diff.stdout.splitlines())
    return not any(path in changed for path in sensitive)


def _evidence(record: object) -> dict:
    if not isinstance(record, dict):
        return {}
    evidence = record.get("evidence")
    return evidence if isinstance(evidence, dict) else {}


def _local_gate(gate: str, record: object, behavior: object) -> list[str]:
    if not isinstance(record, dict) or record.get("result") != "passed":
        return [f"{gate} is not passed"]
    errors = []
    if record.get("skipped") is True or record.get("executed") is False:
        errors.append(f"{gate} was skipped or did not execute")
    if not record.get("command"):
        errors.append(f"{gate} has no command")
    evidence = _evidence(record)
    if not evidence:
        errors.append(f"{gate} has no evidence")
        return errors
    tested = evidence.get("tested_revision")
    if behavior and tested and not _revision_matches(tested, behavior, evidence):
        errors.append(f"{gate} evidence revision does not match the behavior revision")
    errors.extend(_gate_evidence(gate, evidence))
    return errors


def _gate_evidence(gate: str, evidence: dict) -> list[str]:
    errors = []
    if gate == "P20-R1":
        if int(evidence.get("passed") or 0) < 5:
            errors.append(f"{gate} needs the maintenance journeys")
        if evidence.get("separate_process_worker") is not True:
            errors.append(f"{gate} used an in-process-only worker")
    if gate == "P20-R2":
        if not str(evidence.get("migration_head") or "").startswith("0066"):
            errors.append(f"{gate} stopped before the phase 20 head")
        if not str(evidence.get("upgrade_from") or "").startswith("0065"):
            errors.append(f"{gate} did not upgrade a phase 19 database")
        forced = str(evidence.get("forced_rls") or "")
        if evidence.get("runtime") != "false,false" or forced in OLD_RLS or not _complete_rls(forced):
            errors.append(f"{gate} needs the constrained runtime role and a phase 20 row-security count")
    if gate == "P20-R3":
        if evidence.get("thresholds_declared_first") is not True:
            errors.append(f"{gate} measured scale before declaring the threshold")
        if int(evidence.get("cases") or 0) < 200 or int(evidence.get("bound_ms") or 0) != 300:
            errors.append(f"{gate} does not use the declared case count and bound")
        if float(evidence.get("p95_ms") or 9999) >= 300:
            errors.append(f"{gate} exceeded the declared read bound")
    if gate == "P20-R4":
        if evidence.get("executed") is not True or evidence.get("passed") != 12 or evidence.get("exit_code") != 0:
            errors.append(f"{gate} browser journeys did not all pass")
        if list(evidence.get("engines") or []) != list(ENGINES) or list(evidence.get("viewports") or []) != list(VIEWPORTS):
            errors.append(f"{gate} needs Chromium, Firefox, and WebKit at 320, 768, 1024, and 1440")
    if gate == "P20-R6" and (evidence.get("homes") != 20 or evidence.get("past_due_minor") != 427500):
        errors.append(f"{gate} October baseline changed")
    if gate == "P20-R7":
        reviews = evidence.get("review_ids")
        copied = isinstance(reviews, list) and COPIED_REVIEWS.intersection(reviews)
        if evidence.get("independent_review") is not True or not isinstance(reviews, list) or not reviews or copied:
            errors.append(f"{gate} needs an independent phase 20 review")
    if gate == "P20-R8" and evidence.get("pr_head") != evidence.get("tested_revision"):
        errors.append(f"{gate} checked a different pull request head")
    return errors


def _complete_rls(value: str) -> bool:
    parts = value.split("/")
    return len(parts) == 2 and parts[0].isdigit() and parts[0] == parts[1] and int(parts[0]) > 232


def _remote_gate(gate: str, record: dict, state: dict) -> list[str]:
    if record.get("result") != "passed":
        return []
    if gate == "P20-R8":
        return _pr_head(state, record)
    evidence = _evidence(record)
    if evidence.get("merge_commit") != (state.get("merge") or {}).get("commit"):
        return ["P20-R9 merge commit does not match the evidence"]
    return []


def _pr_head(state: dict, record: object) -> list[str]:
    pull = state.get("pull_request") if isinstance(state.get("pull_request"), dict) else {}
    head = pull.get("head")
    evidence = _evidence(record)
    if not head or evidence.get("pr_head") != head:
        return ["P20-R8 pull request head does not match the evidence"]
    if not isinstance(record, dict) or record.get("result") != "passed":
        return ["P20-R8 is not passed on the pull request head"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mode", choices=("local", "pr"), default="local")
    args = parser.parse_args()
    if not args.check:
        parser.error("use --check")
    if not EVIDENCE.exists():
        print("phase20 acceptance incomplete: no evidence file")
        return 1
    errors = evaluate(json.loads(EVIDENCE.read_text(encoding="utf-8")), args.mode)
    if errors:
        print("phase20 acceptance incomplete:")
        for error in errors:
            print("-", error)
        return 1
    print("phase20 acceptance passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

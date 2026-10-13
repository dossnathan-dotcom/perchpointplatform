"""Phase 21 acceptance checker. A targeted file is not acceptance."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_reports" / "phase21" / "acceptance-state.json"
LOCAL_GATES = tuple(f"P21-R{index}" for index in range(8))
REMOTE_GATES = ("P21-R8", "P21-R9")
ENGINES = ("chromium", "firefox", "webkit")
VIEWPORTS = (320, 768, 1024, 1440)
COPIED_REVIEWS = {
    "bd9596a9-ebf6-4ea1-8ae9-38c6c386b1ac",
    "43536cba-52de-4e4d-8ff0-e7653ca2ce72",
    "1769e37a-ec1f-4ba8-88cb-6ebf12bea993",
    "f79fd4e5-510c-40a1-80e2-f68f6099cb53",
    "10f48972-03f0-41c6-91fc-7d296557da45",
}
OLD_RLS = {"226/226", "232/232", "251/251"}


def evaluate(state: dict, mode: str = "local") -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["acceptance state is missing"]
    if state.get("real_values_activated") is not False or state.get("money_moved") is not False:
        errors.append("local evidence must keep real values and money movement closed")
    if state.get("phase") != 21:
        errors.append("this record is not the phase 21 acceptance")
    gates = state.get("gates") if isinstance(state.get("gates"), dict) else {}
    if _is_targeted_checkpoint(state):
        errors.append("a targeted call file is not phase acceptance")
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
        errors.extend(_pr_head(state, gates.get("P21-R8")))
        return errors
    errors.append(f"unknown acceptance mode {mode}")
    return errors


def _is_targeted_checkpoint(state: dict) -> bool:
    results = state.get("results") if isinstance(state.get("results"), dict) else {}
    commands = " ".join(state.get("commands") or [])
    if "phase21_clean_room" in commands and "playwright.phase21.config.js" in commands:
        return False
    return "test_calls.py" in commands and "passed" in str(results.get("pytest", ""))


def _revision_matches(tested: object, behavior: object, evidence: dict) -> bool:
    if tested == behavior:
        return True
    if evidence.get("ancestor_revision") != tested:
        return False
    sensitive = evidence.get("sensitive_paths")
    if not isinstance(sensitive, list) or not sensitive:
        return False
    try:
        ancestor = subprocess.run(["git", "merge-base", "--is-ancestor", str(tested), str(behavior)], cwd=ROOT, check=False, capture_output=True)
        diff = subprocess.run(["git", "diff", "--name-only", f"{tested}..{behavior}"], cwd=ROOT, check=False, capture_output=True, text=True)
    except OSError:
        return False
    if ancestor.returncode != 0 or diff.returncode != 0:
        return False
    changed = set(diff.stdout.splitlines())
    return not any(path in changed for path in sensitive)


def _local_gate(gate: str, record: object, behavior: object) -> list[str]:
    if not isinstance(record, dict) or record.get("result") != "passed":
        return [f"{gate} is not passed"]
    errors = []
    if not record.get("command"):
        errors.append(f"{gate} has no command")
    evidence = record.get("evidence") if isinstance(record.get("evidence"), dict) else {}
    if not evidence:
        return errors + [f"{gate} has no evidence"]
    tested = evidence.get("tested_revision")
    if behavior and tested and not _revision_matches(tested, behavior, evidence):
        errors.append(f"{gate} evidence revision does not match the behavior revision")
    if gate == "P21-R1":
        if int(evidence.get("passed") or 0) < 4 or evidence.get("separate_process_worker") is not True:
            errors.append(f"{gate} needs the call journeys and a separate worker")
    if gate == "P21-R2":
        if not str(evidence.get("migration_head") or "").startswith("0067"):
            errors.append(f"{gate} stopped before the phase 21 head")
        if not str(evidence.get("upgrade_from") or "").startswith("0066"):
            errors.append(f"{gate} did not upgrade a phase 20 database")
        forced = str(evidence.get("forced_rls") or "")
        parts = forced.split("/")
        complete = len(parts) == 2 and parts[0] == parts[1] and parts[0].isdigit() and int(parts[0]) > 251
        if evidence.get("runtime") != "false,false" or forced in OLD_RLS or not complete:
            errors.append(f"{gate} needs the constrained runtime role and a phase 21 row-security count")
    if gate == "P21-R3":
        if evidence.get("thresholds_declared_first") is not True or int(evidence.get("interactions") or 0) < 200:
            errors.append(f"{gate} measured scale before the declared interaction count")
        if float(evidence.get("p95_ms") or 9999) >= 300:
            errors.append(f"{gate} exceeded the declared read bound")
    if gate == "P21-R4":
        if evidence.get("passed") != 12 or list(evidence.get("engines") or []) != list(ENGINES) or list(evidence.get("viewports") or []) != list(VIEWPORTS):
            errors.append(f"{gate} needs Chromium, Firefox, and WebKit at 320, 768, 1024, and 1440")
    if gate == "P21-R6" and (evidence.get("homes") != 20 or evidence.get("past_due_minor") != 427500):
        errors.append(f"{gate} October baseline changed")
    if gate == "P21-R7":
        reviews = evidence.get("review_ids")
        copied = isinstance(reviews, list) and COPIED_REVIEWS.intersection(reviews)
        if evidence.get("independent_review") is not True or not isinstance(reviews, list) or not reviews or copied:
            errors.append(f"{gate} needs an independent phase 21 review")
    return errors


def _remote_gate(gate: str, record: dict, state: dict) -> list[str]:
    if record.get("result") != "passed":
        return []
    if gate == "P21-R8":
        return _pr_head(state, record)
    evidence = record.get("evidence") if isinstance(record.get("evidence"), dict) else {}
    if evidence.get("merge_commit") != (state.get("merge") or {}).get("commit"):
        return ["P21-R9 merge commit does not match the evidence"]
    return []


def _pr_head(state: dict, record: object) -> list[str]:
    pull = state.get("pull_request") if isinstance(state.get("pull_request"), dict) else {}
    evidence = record.get("evidence") if isinstance(record, dict) and isinstance(record.get("evidence"), dict) else {}
    if not pull.get("head") or evidence.get("pr_head") != pull.get("head"):
        return ["P21-R8 pull request head does not match the evidence"]
    if not isinstance(record, dict) or record.get("result") != "passed":
        return ["P21-R8 is not passed on the pull request head"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mode", choices=("local", "pr"), default="local")
    args = parser.parse_args()
    if not args.check:
        parser.error("use --check")
    if not EVIDENCE.exists():
        print("phase21 acceptance incomplete: no evidence file")
        return 1
    errors = evaluate(json.loads(EVIDENCE.read_text(encoding="utf-8")), args.mode)
    if errors:
        print("phase21 acceptance incomplete:")
        for error in errors:
            print("-", error)
        return 1
    print("phase21 acceptance passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

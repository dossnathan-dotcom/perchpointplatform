"""Phase 19 acceptance checker. A six-test file is not acceptance."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_reports" / "phase19" / "acceptance-state.json"
LOCAL_GATES = tuple(f"P19-R{index}" for index in range(8))
REMOTE_GATES = ("P19-R8", "P19-R9")
ENGINES = ("chromium", "firefox", "webkit")
VIEWPORTS = (320, 768, 1024, 1440)
SELF_REVIEW = {"implementer", "self", "author", "phase18-invariant-review", "phase19-invariant-review"}
PHASE18_REVIEWS = {
    "bd9596a9-ebf6-4ea1-8ae9-38c6c386b1ac",
    "43536cba-52de-4e4d-8ff0-e7653ca2ce72",
}


def evaluate(state: dict, mode: str = "local") -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["acceptance state is missing"]
    if state.get("real_values_activated") is not False or state.get("money_moved") is not False:
        errors.append("local evidence must keep real values and money movement closed")
    if state.get("phase_20_started") is True:
        errors.append("phase 20 must stay unopened")
    if state.get("phase") != 19:
        errors.append("this record is not the phase 19 acceptance")
    gates = state.get("gates") if isinstance(state.get("gates"), dict) else {}
    if any(str(name).startswith("P18-") for name in gates):
        errors.append("a phase 18 gate does not qualify phase 19")
    if _is_targeted_checkpoint(state):
        errors.append("the six-test reconciliation file is not phase acceptance")
    findings = state.get("findings") if isinstance(state.get("findings"), list) else []
    if any(isinstance(item, dict) and item.get("disposition") == "OPEN" for item in findings):
        errors.append("an unresolved blocking finding is still open")
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
        errors.extend(_pr_head(state, gates.get("P19-R8")))
        return errors
    errors.append(f"unknown acceptance mode {mode}")
    return errors


def _is_targeted_checkpoint(state: dict) -> bool:
    results = state.get("results") if isinstance(state.get("results"), dict) else {}
    pytest_result = str(results.get("pytest", ""))
    commands = " ".join(state.get("commands") or [])
    if "6 passed" not in pytest_result:
        return False
    if "phase19_clean_room" in commands and "playwright.phase19.config.js" in commands:
        return False
    return "test_reconciliation.py" in commands


def _revision_matches(tested: object, behavior: object, evidence: dict) -> bool:
    if tested == behavior:
        return True
    if evidence.get("ancestor_revision") != tested:
        return False
    sensitive = evidence.get("sensitive_paths")
    if not isinstance(sensitive, list) or not sensitive or not all(isinstance(path, str) and path for path in sensitive):
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
    if gate == "P19-R1" and int(evidence.get("passed") or 0) < 6:
        errors.append(f"{gate} needs the reconciliation tests")
    if gate == "P19-R2":
        if not str(evidence.get("migration_head") or "").startswith("0065"):
            errors.append(f"{gate} stopped before the phase 19 head")
        if not str(evidence.get("upgrade_from") or "").startswith("0064"):
            errors.append(f"{gate} did not upgrade a phase 18 database")
        if evidence.get("accounts_preserved") != 15:
            errors.append(f"{gate} did not keep the seeded accounts")
        if evidence.get("runtime") != "false,false" or evidence.get("forced_rls") != "232/232":
            errors.append(f"{gate} needs the constrained runtime role and the phase 19 row-security count")
    if gate == "P19-R3":
        if evidence.get("thresholds_declared_first") is not True:
            errors.append(f"{gate} measured scale before declaring the threshold")
        if evidence.get("lines") != 200 or int(evidence.get("bound_ms") or 0) != 300:
            errors.append(f"{gate} does not use the declared line count and bound")
        if float(evidence.get("p95_ms") or 9999) >= 300:
            errors.append(f"{gate} exceeded the declared read bound")
    if gate == "P19-R4":
        if evidence.get("executed") is not True or evidence.get("passed") != 12 or evidence.get("exit_code") != 0:
            errors.append(f"{gate} browser journeys did not all pass")
        if list(evidence.get("engines") or []) != list(ENGINES) or list(evidence.get("viewports") or []) != list(VIEWPORTS):
            errors.append(f"{gate} needs Chromium, Firefox, and WebKit at 320, 768, 1024, and 1440")
    if gate == "P19-R6" and (evidence.get("homes") != 20 or evidence.get("households") != 20):
        errors.append(f"{gate} catalog is no longer 20 homes and 20 households")
    if gate == "P19-R7":
        reviewer = str(evidence.get("reviewer") or "")
        folded = reviewer.casefold()
        reviews = evidence.get("review_ids")
        copied = isinstance(reviews, list) and PHASE18_REVIEWS.intersection(reviews)
        if (
            evidence.get("independent_review") is not True
            or folded in SELF_REVIEW
            or "invariant-review" in folded
            or not isinstance(reviews, list)
            or not reviews
            or copied
            or not all(isinstance(item, str) and item for item in reviews)
        ):
            errors.append(f"{gate} needs a separate phase 19 review")
    if gate == "P19-R8" and evidence.get("pr_head") != evidence.get("tested_revision"):
        errors.append(f"{gate} checked a different pull request head")
    return errors


def _remote_gate(gate: str, record: dict, state: dict) -> list[str]:
    if record.get("result") != "passed":
        return []
    if gate == "P19-R8":
        return _pr_head(state, record)
    evidence = _evidence(record)
    if evidence.get("merge_commit") != (state.get("merge") or {}).get("commit"):
        return ["P19-R9 merge commit does not match the evidence"]
    return []


def _pr_head(state: dict, record: object) -> list[str]:
    pull = state.get("pull_request") if isinstance(state.get("pull_request"), dict) else {}
    head = pull.get("head")
    evidence = _evidence(record)
    if not head or evidence.get("pr_head") != head:
        return ["P19-R8 pull request head does not match the evidence"]
    if not isinstance(record, dict) or record.get("result") != "passed":
        return ["P19-R8 is not passed on the pull request head"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mode", choices=("local", "pr"), default="local")
    args = parser.parse_args()
    if not args.check:
        parser.error("use --check")
    if not EVIDENCE.exists():
        print("phase19 acceptance incomplete: no evidence file")
        return 1
    errors = evaluate(json.loads(EVIDENCE.read_text(encoding="utf-8")), args.mode)
    if errors:
        print("phase19 acceptance incomplete:")
        for error in errors:
            print("-", error)
        return 1
    print("phase19 acceptance passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

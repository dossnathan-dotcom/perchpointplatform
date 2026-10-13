"""Phase 18 acceptance checker. A passed assistance file is not acceptance."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_reports" / "phase18" / "acceptance-state.json"
LOCAL_GATES = tuple(f"P18-R{index}" for index in range(17))
REMOTE_GATES = ("P18-R17", "P18-R18")
ENGINES = ("chromium", "firefox", "webkit")
VIEWPORTS = (320, 768, 1024, 1440)
SELF_REVIEW = {"implementer", "self", "author", "phase18-invariant-review"}


def evaluate(state: dict, mode: str = "local") -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["acceptance state is missing"]
    if state.get("real_values_activated") is not False or state.get("money_moved") is not False:
        errors.append("local evidence must keep real values and money movement closed")
    if state.get("phase_19_started") is True:
        errors.append("phase 19 must stay unopened in the phase 18 record")
    gates = state.get("gates") if isinstance(state.get("gates"), dict) else {}
    if _is_targeted_checkpoint(state):
        errors.append("the targeted assistance checkpoint is not phase acceptance")
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
        errors.extend(_pr_head(state, gates.get("P18-R17")))
        return errors
    errors.append(f"unknown acceptance mode {mode}")
    return errors


def _is_targeted_checkpoint(state: dict) -> bool:
    results = state.get("results") if isinstance(state.get("results"), dict) else {}
    pytest_result = str(results.get("pytest", ""))
    commands = " ".join(state.get("commands") or [])
    if "18 passed" not in pytest_result and "17 passed" not in pytest_result:
        return False
    if "playwright" in commands or "phase18_clean_room" in commands:
        return False
    return "test_assistance.py" in commands


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
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
        diff = subprocess.run(
            ["git", "diff", "--name-only", f"{tested}..{behavior}"],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
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
    if gate == "P18-R2":
        head = str(evidence.get("migration_head") or "")
        if head == "0060_phase17_grant_accept" or not head.startswith("0064"):
            errors.append(f"{gate} clean room stopped before the phase 18 head")
        if evidence.get("runtime_role") != "NOSUPERUSER" or evidence.get("forced_rls") is not True:
            errors.append(f"{gate} needs the constrained runtime role and forced row security")
    if gate == "P18-R10" and evidence.get("worker") != "process":
        errors.append(f"{gate} needs a separate worker process")
    if gate == "P18-R12":
        if evidence.get("executed") is not True:
            errors.append(f"{gate} browser matrix did not execute")
        if list(evidence.get("engines") or []) != list(ENGINES) or list(evidence.get("viewports") or []) != list(VIEWPORTS):
            errors.append(f"{gate} needs Chromium, Firefox, and WebKit at 320, 768, 1024, and 1440")
    if gate == "P18-R14" and str(evidence.get("clean_room_head") or "").startswith("0060"):
        errors.append(f"{gate} uses the phase 17 head as the phase 18 clean room")
    if gate == "P18-R16":
        reviewer = str(evidence.get("reviewer") or "")
        folded = reviewer.casefold()
        if evidence.get("independent_review") is not True or folded in SELF_REVIEW or "invariant-review" in folded:
            errors.append(f"{gate} needs an independent review of the current candidate")
    if gate == "P18-R17" and evidence.get("pr_head") != evidence.get("tested_revision"):
        errors.append(f"{gate} checked a different pull request head")
    return errors


def _remote_gate(gate: str, record: dict, state: dict) -> list[str]:
    if record.get("result") != "passed":
        return []
    if gate == "P18-R17":
        return _pr_head(state, record)
    evidence = _evidence(record)
    if evidence.get("merge_commit") != (state.get("merge") or {}).get("commit"):
        return ["P18-R18 merge commit does not match the evidence"]
    return []


def _pr_head(state: dict, record: object) -> list[str]:
    pull = state.get("pull_request") if isinstance(state.get("pull_request"), dict) else {}
    head = pull.get("head")
    evidence = _evidence(record)
    if not head or evidence.get("pr_head") != head:
        return ["P18-R17 pull request head does not match the evidence"]
    if not isinstance(record, dict) or record.get("result") != "passed":
        return ["P18-R17 is not passed on the pull request head"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mode", choices=("local", "pr"), default="local")
    args = parser.parse_args()
    if not args.check:
        parser.error("use --check")
    if not EVIDENCE.exists():
        print("phase18 acceptance incomplete: no evidence file")
        return 1
    errors = evaluate(json.loads(EVIDENCE.read_text(encoding="utf-8")), args.mode)
    if errors:
        print("phase18 acceptance incomplete:")
        for error in errors:
            print("-", error)
        return 1
    print("phase18 acceptance passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

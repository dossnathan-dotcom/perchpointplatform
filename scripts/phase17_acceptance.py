"""Phase 17 acceptance checker. A passed status is not evidence."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "test_reports" / "phase17" / "acceptance-state.json"
LOCAL_GATES = tuple(f"P17-R{index}" for index in range(17))
REMOTE_GATES = ("P17-R17", "P17-R18")
AUTOPAY_CASES = tuple(f"APW-{index:02d}" for index in range(1, 10))
ENGINES = ("chromium", "firefox", "webkit")
VIEWPORTS = (320, 768, 1024, 1440)
SELF_REVIEW = {"implementer", "self", "author"}


def evaluate(state: dict, mode: str = "local") -> list[str]:
    errors: list[str] = []
    if not isinstance(state, dict):
        return ["acceptance state is missing"]
    if state.get("real_values_activated") is not False or state.get("money_moved") is not False:
        errors.append("local evidence must keep real values and money movement closed")
    if state.get("phase_18_started") is True:
        errors.append("phase 18 must stay unopened")
    gates = state.get("gates") if isinstance(state.get("gates"), dict) else {}
    if _is_original_checkpoint(state, gates):
        errors.append("the original 15-test checkpoint is not phase acceptance")
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
        errors.extend(_pr_head(state, gates.get("P17-R17")))
        return errors
    errors.append(f"unknown acceptance mode {mode}")
    return errors


def _is_original_checkpoint(state: dict, gates: dict) -> bool:
    results = state.get("results") if isinstance(state.get("results"), dict) else {}
    pytest_result = str(results.get("pytest", ""))
    commands = " ".join(state.get("commands") or [])
    if "15 passed" not in pytest_result:
        return False
    if "phase17_worker" in commands or "playwright" in commands:
        return False
    for gate in ("P17-R7", "P17-R11"):
        evidence = _evidence(gates.get(gate))
        if evidence.get("worker") == "process":
            return False
    return True


def _revision_matches(tested: object, behavior: object, evidence: dict) -> bool:
    """Same revision matches. An ancestor matches only when its sensitive paths are unchanged."""
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
    if evidence.get("kind") == "screenshot" and "settlement_count" not in evidence and "effect_count" not in evidence:
        errors.append(f"{gate} screenshot has no financial effect evidence")
    errors.extend(_gate_evidence(gate, evidence))
    return errors


def _gate_evidence(gate: str, evidence: dict) -> list[str]:
    errors = []
    if gate in {"P17-R4", "P17-R6", "P17-R12"} and evidence.get("ledger_status") == "not_linked":
        errors.append(f"{gate} uses a not_linked fixture as the linked household journey")
    if gate == "P17-R6":
        if evidence.get("ledger_status") != "posted" or evidence.get("settlement_count") != 2:
            errors.append(f"{gate} needs two posted settlements on the linked account")
        if evidence.get("replay") != "single":
            errors.append(f"{gate} needs a replay that does not add a settlement")
    if gate == "P17-R4" and evidence.get("browser") is not True:
        errors.append(f"{gate} needs the invitation journey in the browser")
    if gate in {"P17-R7", "P17-R11"} and evidence.get("worker") == "in_process":
        errors.append(f"{gate} uses an in-process inbox call as an independent worker")
    if gate == "P17-R7":
        if evidence.get("worker") != "process":
            errors.append(f"{gate} needs a separate worker process")
        cases = evidence.get("cases") if isinstance(evidence.get("cases"), list) else []
        missing = [case for case in AUTOPAY_CASES if case not in cases]
        if missing:
            errors.append(f"{gate} is missing autopay cases {', '.join(missing)}")
    if gate == "P17-R11" and evidence.get("worker") != "process":
        errors.append(f"{gate} needs the callback route consumed by a separate worker")
    if gate == "P17-R9" and evidence.get("concurrent") is not True:
        errors.append(f"{gate} needs concurrent refund evidence")
    if gate == "P17-R14":
        if evidence.get("executed") is not True:
            errors.append(f"{gate} browser matrix did not execute")
        if list(evidence.get("engines") or []) != list(ENGINES) or list(evidence.get("viewports") or []) != list(VIEWPORTS):
            errors.append(f"{gate} needs Chromium, Firefox, and WebKit at 320, 768, 1024, and 1440")
    if gate == "P17-R16":
        reviewer = str(evidence.get("reviewer") or "")
        if evidence.get("independent_review") is not True or reviewer.casefold() in SELF_REVIEW:
            errors.append(f"{gate} needs an independent review of the current candidate")
        if evidence.get("households") != 20:
            errors.append(f"{gate} needs the twenty-household demonstration")
    if gate == "P17-R5" and evidence.get("sandbox") not in {"unrun", "passed"}:
        errors.append(f"{gate} must label sandbox execution as unrun or passed")
    if gate == "P17-R1":
        head = str(evidence.get("migration_head") or "")
        revision = int(head.split("_", 1)[0]) if head[:4].isdigit() else 0
        if revision < 52 and not evidence.get("migration_successor"):
            errors.append(f"{gate} needs the 0052 payload migration or a later successor")
    return errors


def _remote_gate(gate: str, record: dict, state: dict) -> list[str]:
    if record.get("result") != "passed":
        return []
    return _pr_head(state, record) if gate == "P17-R17" else []


def _pr_head(state: dict, record: object) -> list[str]:
    pull = state.get("pull_request") if isinstance(state.get("pull_request"), dict) else {}
    head = pull.get("head")
    evidence = _evidence(record)
    if not head or evidence.get("pr_head") != head:
        return ["P17-R17 pull request head does not match the evidence"]
    if not isinstance(record, dict) or record.get("result") != "passed":
        return ["P17-R17 is not passed on the pull request head"]
    return []


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--mode", choices=("local", "pr"), default="local")
    args = parser.parse_args()
    if not args.check:
        parser.error("use --check")
    if not EVIDENCE.exists():
        print("phase17 acceptance incomplete: no evidence file")
        return 1
    errors = evaluate(json.loads(EVIDENCE.read_text(encoding="utf-8")), args.mode)
    if errors:
        print("phase17 acceptance incomplete:")
        for error in errors:
            print("-", error)
        return 1
    print("phase17 acceptance passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())

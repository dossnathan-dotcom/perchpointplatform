"""Fail closed unless Phase 7 evidence covers the repository-bound gates.

P7-R0 through P7-R16 are local. P7-R17 is the pull-request head. P7-R18 is the
merged main workflow. Hosted, stakeholder, legal, and production stay separate.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from validate_phase7_answers import questions, validate_substance  # noqa: E402

ANSWERS = ROOT / "docs/plans/phase7/APPROVED_CUSTOMIZATION_ANSWERS.md"
TRACE = ROOT / "docs/plans/phase7/ANSWER_TRACEABILITY.md"
EVIDENCE = ROOT / "test_reports" / "phase7" / "acceptance-state.json"
LOCAL_GATES = tuple(f"P7-R{index}" for index in range(17))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if not args.check:
        parser.error("use --check")
    answers = questions(ANSWERS)
    trace = questions(TRACE)
    expected = set(range(1, 121))
    errors = []
    if set(answers) != expected or set(trace) != expected:
        errors.append("P7-R1 answer or trace coverage is incomplete")
    errors.extend(f"P7-R1 {item}" for item in validate_substance(answers, trace))
    if not EVIDENCE.exists():
        errors.append("P7-R0 through P7-R16 have no structured evidence file")
    else:
        state = json.loads(EVIDENCE.read_text(encoding="utf-8"))
        gates = state.get("gates") if isinstance(state, dict) else None
        if not isinstance(gates, dict):
            errors.append("P7 evidence is missing a gates object")
        else:
            for gate in LOCAL_GATES:
                record = gates.get(gate)
                if not isinstance(record, dict):
                    errors.append(f"{gate} evidence record is missing")
                    continue
                if record.get("result") != "passed":
                    errors.append(f"{gate} result is not passed")
                if not record.get("command") or not record.get("tested_commit"):
                    errors.append(f"{gate} is missing a command or tested commit")
    print("phase7 local acceptance: NOT GRANTED" if errors else "phase7 local acceptance: GRANTED")
    print("answers:", len(answers), "trace:", len(trace))
    print("external: hosted BLOCKED; stakeholder BLOCKED; legal BLOCKED; production NOT AUTHORIZED")
    for gate in LOCAL_GATES:
        print(f"{gate}: INCOMPLETE")
    print("P7-R17: not a repository-bound gate")
    print("P7-R18: not a repository-bound gate")
    if errors:
        print("blocked:")
        for error in errors[:12]:
            print("-", error)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

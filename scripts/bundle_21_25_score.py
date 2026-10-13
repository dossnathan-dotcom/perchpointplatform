"""Score Phases 21–25 only from executed evidence. A hand-edited flag is not enough."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CRITERIA = ROOT / "test_reports" / "phases21-25" / "bundle-criteria.json"
EVIDENCE = ROOT / "test_reports" / "phases21-25" / "bundle-evidence.json"


def score(criteria: dict, evidence: dict) -> tuple[int, list[str]]:
    errors: list[str] = []
    if criteria.get("frozen") is not True or len(criteria.get("units") or []) != 20:
        return 0, ["criteria are not the frozen twenty units"]
    units = {item["id"]: item for item in criteria["units"]}
    recorded = evidence.get("units") if isinstance(evidence.get("units"), dict) else {}
    total = 0
    for unit_id, spec in units.items():
        row = recorded.get(unit_id) if isinstance(recorded.get(unit_id), dict) else {}
        claimed = row.get("passed") is True
        sub = row.get("subcriteria") if isinstance(row.get("subcriteria"), dict) else {}
        required = spec["subcriteria"]
        complete = all(sub.get(name, {}).get("result") == "passed" for name in required)
        command_ok = bool(row.get("command")) and row.get("exit_code") == 0 and bool(row.get("report"))
        if claimed and not (complete and command_ok):
            errors.append(f"{unit_id} claims a pass without executed subcriteria")
            continue
        if complete and command_ok:
            total += int(criteria.get("points_per_unit") or 0)
    gates = evidence.get("gates") if isinstance(evidence.get("gates"), dict) else {}
    for gate in criteria.get("gates") or []:
        row = gates.get(gate) if isinstance(gates.get(gate), dict) else {}
        if row.get("result") == "passed" and row.get("exit_code") != 0:
            errors.append(f"{gate} was marked passed without an executed result")
    return total, errors


def main() -> int:
    criteria = json.loads(CRITERIA.read_text(encoding="utf-8"))
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8")) if EVIDENCE.exists() else {"units": {}, "gates": {}}
    total, errors = score(criteria, evidence)
    print(f"bundle_score={total}/100")
    for error in errors:
        print(error)
    if errors:
        return 1
    if "--require-complete" in sys.argv and total != 100:
        print("bundle score is incomplete")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Checker regression: evidence commits cannot change runtime files."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "scripts"))

from phase7_acceptance import diff_is_evidence_only, evaluate_gates, path_is_evidence_only


def _state():
    gates = {
        f"P7-R{index}": {"result": "passed", "exit_code": 0, "command": "python -m pytest", "tested_commit": "b" * 40}
        for index in range(17)
    }
    return {"behavior_commit": "b" * 40, "gates": gates}


def test_runtime_paths_are_not_evidence_only():
    assert path_is_evidence_only("test_reports/phase7/acceptance-state.json")
    assert path_is_evidence_only("docs/plans/phase7/ACCEPTANCE_REPORT.md")
    assert not path_is_evidence_only("backend/perchpoint/phase7_routes.py")
    assert not path_is_evidence_only("scripts/phase7_acceptance.py")
    assert not diff_is_evidence_only(["test_reports/phase7/acceptance-state.json", "backend/perchpoint/routes.py"])


def test_checker_rejects_a_behavior_commit_that_claims_to_be_evidence():
    errors = evaluate_gates(_state(), "b" * 40, [])
    assert any("descendant" in error for error in errors)


def test_checker_accepts_an_evidence_only_child():
    errors = evaluate_gates(_state(), "e" * 40, ["test_reports/phase7/acceptance-state.json"])
    assert errors == []


def test_checker_rejects_a_failed_gate():
    state = _state()
    state["gates"]["P7-R11"]["exit_code"] = 1
    state["gates"]["P7-R11"]["result"] = "failed"
    errors = evaluate_gates(state, "e" * 40, ["docs/plans/phase7/REVIEW_FINDINGS.md"])
    assert any("P7-R11" in error for error in errors)

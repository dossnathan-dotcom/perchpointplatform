"""The Phase 17 checker rejects status flips and insufficient evidence."""
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from phase17_acceptance import evaluate  # noqa: E402


def _complete() -> dict:
    evidence = {
        "P17-R0": {"baseline": True, "decisions": True},
        "P17-R1": {"migration_head": "0052_phase17_event_payload", "clean_room": True, "predecessor_upgrade": True},
        "P17-R2": {"runtime_role": "NOSUPERUSER", "forced_rls": True},
        "P17-R3": {"published_charge": True, "pre_activation": True},
        "P17-R4": {"invitation": True, "browser": True, "ledger_status": "posted"},
        "P17-R5": {"adapter_contract": True, "sandbox": "unrun"},
        "P17-R6": {"ledger_status": "posted", "settlement_count": 2, "replay": "single"},
        "P17-R7": {"worker": "process", "cases": [f"APW-{index:02d}" for index in range(1, 10)]},
        "P17-R8": {"returns": True, "uncertainty": True},
        "P17-R9": {"concurrent": True},
        "P17-R10": {"closed_period": True},
        "P17-R11": {"worker": "process", "callback_route": "/api/v2/payments/provider-events"},
        "P17-R12": {"personas": ["resident", "payer", "operations", "owner"], "ledger_status": "posted"},
        "P17-R13": {"negative_access": True},
        "P17-R14": {"executed": True, "engines": ["chromium", "firefox", "webkit"], "viewports": [320, 768, 1024, 1440]},
        "P17-R15": {"scale": True},
        "P17-R16": {"independent_review": True, "reviewer": "separate-reviewer", "households": 20},
    }
    gates = {
        gate: {"result": "passed", "command": f"recorded {gate}", "evidence": {**payload, "tested_revision": "candidate"}}
        for gate, payload in evidence.items()
    }
    gates["P17-R17"] = {"result": "not_run"}
    gates["P17-R18"] = {"result": "not_run"}
    return {
        "behavior_revision": "candidate",
        "real_values_activated": False,
        "money_moved": False,
        "phase_18_started": False,
        "results": {"pytest": "candidate suite"},
        "commands": ["python -m pytest tests/phase17 -n 0"],
        "gates": gates,
        "findings": [],
    }


def test_complete_local_evidence_can_pass_while_sandbox_stays_unrun():
    assert evaluate(_complete(), "local") == []


def test_flipping_the_15_test_checkpoint_to_passed_is_rejected():
    state = {
        "real_values_activated": False,
        "money_moved": False,
        "phase_18_started": False,
        "commands": ["python -m pytest tests/phase17/test_payments.py tests/phase17/test_refund_policy.py -n 0"],
        "results": {"pytest": "15 passed, exit 0, 28.46s, 2026-10-11"},
        "gates": {gate: {"result": "partial"} for gate in (f"P17-R{index}" for index in range(19))},
    }
    for record in state["gates"].values():
        record["result"] = "passed"
    errors = evaluate(state, "local")
    assert any("15-test checkpoint" in error for error in errors)
    assert any("no evidence" in error for error in errors)


def test_not_linked_fixture_is_not_the_linked_household_journey():
    state = _complete()
    state["gates"]["P17-R6"]["evidence"]["ledger_status"] = "not_linked"
    errors = evaluate(state, "local")
    assert any("not_linked" in error for error in errors)


def test_in_process_inbox_call_is_not_an_independent_worker():
    state = _complete()
    state["gates"]["P17-R7"]["evidence"]["worker"] = "in_process"
    errors = evaluate(state, "local")
    assert any("in-process" in error for error in errors)


def test_screenshot_without_effect_evidence_is_rejected():
    state = _complete()
    state["gates"]["P17-R12"]["evidence"] = {"kind": "screenshot", "tested_revision": "candidate"}
    errors = evaluate(state, "local")
    assert any("screenshot" in error for error in errors)


def test_stale_revision_open_finding_and_skipped_job_are_rejected():
    state = _complete()
    state["gates"]["P17-R9"]["evidence"]["tested_revision"] = "older"
    state["gates"]["P17-R14"]["executed"] = False
    state["findings"] = [{"id": "F-1", "disposition": "OPEN"}]
    errors = evaluate(state, "local")
    assert any("revision" in error for error in errors)
    assert any("skipped" in error for error in errors)
    assert any("blocking finding" in error for error in errors)


def test_self_review_and_missing_autopay_cases_are_rejected():
    state = _complete()
    state["gates"]["P17-R16"]["evidence"]["reviewer"] = "implementer"
    state["gates"]["P17-R7"]["evidence"]["cases"] = ["APW-01"]
    errors = evaluate(state, "local")
    assert any("independent review" in error for error in errors)
    assert any("APW-02" in error for error in errors)


def test_invariant_script_cannot_close_the_review_gate():
    state = _complete()
    state["findings"] = []
    state["gates"]["P17-R16"]["evidence"]["reviewer"] = "phase17-invariant-review"
    state["gates"]["P17-R16"]["evidence"]["independent_review"] = True
    errors = evaluate(state, "local")
    assert any("independent review" in error for error in errors)


def test_pr_mode_rejects_a_mismatched_head():
    state = _complete()
    state["pull_request"] = {"head": "abc123"}
    state["gates"]["P17-R17"] = {
        "result": "passed",
        "command": "gh pr checks",
        "evidence": {"pr_head": "def456", "tested_revision": "candidate"},
    }
    errors = evaluate(state, "pr")
    assert any("head does not match" in error for error in errors)


BEHAVIOR = "668ee1b3828dcc457bc9e5a8b795fa1eb42a9734"
ANCESTOR = "9a5c20341d7be596bf65ec5cf2659aad8b0111a5"


def _require_recorded_history() -> None:
    try:
        probe = subprocess.run(
            ["git", "merge-base", "--is-ancestor", ANCESTOR, BEHAVIOR],
            cwd=ROOT,
            check=False,
            capture_output=True,
        )
    except OSError:
        pytest.skip("git cannot read the recorded Phase 17 revisions here")
    if probe.returncode != 0:
        pytest.skip("git cannot read the recorded Phase 17 revisions here")


def test_ancestor_evidence_holds_when_its_sensitive_paths_are_unchanged():
    _require_recorded_history()
    state = _complete()
    state["behavior_revision"] = BEHAVIOR
    evidence = state["gates"]["P17-R14"]["evidence"]
    evidence["tested_revision"] = ANCESTOR
    evidence["ancestor_revision"] = ANCESTOR
    evidence["sensitive_paths"] = ["frontend/e2e/phase17-payer.spec.js"]
    errors = evaluate(state, "local")
    assert not any("P17-R14 evidence revision" in error for error in errors)


def test_ancestor_evidence_is_rejected_when_a_sensitive_path_changed():
    _require_recorded_history()
    state = _complete()
    state["behavior_revision"] = BEHAVIOR
    evidence = state["gates"]["P17-R6"]["evidence"]
    evidence["tested_revision"] = ANCESTOR
    evidence["ancestor_revision"] = ANCESTOR
    evidence["sensitive_paths"] = ["backend/perchpoint/phase17_payments.py"]
    errors = evaluate(state, "local")
    assert any("P17-R6 evidence revision" in error for error in errors)


def test_ancestor_claim_without_sensitive_paths_is_rejected():
    state = _complete()
    state["behavior_revision"] = BEHAVIOR
    evidence = state["gates"]["P17-R15"]["evidence"]
    evidence["tested_revision"] = ANCESTOR
    evidence["ancestor_revision"] = ANCESTOR
    errors = evaluate(state, "local")
    assert any("P17-R15 evidence revision" in error for error in errors)

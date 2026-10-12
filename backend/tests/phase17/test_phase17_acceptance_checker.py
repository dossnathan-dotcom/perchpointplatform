"""The Phase 17 checker rejects status flips and insufficient evidence."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from phase17_acceptance import EVIDENCE, evaluate  # noqa: E402


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
    state = json.loads(EVIDENCE.read_text(encoding="utf-8"))
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

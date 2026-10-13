"""The Phase 21 checker rejects a targeted file, an older head, and a copied review."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from phase21_acceptance import evaluate  # noqa: E402


def _complete() -> dict:
    evidence = {
        "P21-R0": {"scope": "calls"},
        "P21-R1": {"passed": 4, "exit_code": 0, "separate_process_worker": True},
        "P21-R2": {
            "migration_head": "0067_phase21_calls",
            "upgrade_from": "0066_phase20_maintenance",
            "runtime": "false,false",
            "forced_rls": "260/260",
        },
        "P21-R3": {"thresholds_declared_first": True, "interactions": 200, "p95_ms": 40.0},
        "P21-R4": {
            "passed": 12,
            "exit_code": 0,
            "engines": ["chromium", "firefox", "webkit"],
            "viewports": [320, 768, 1024, 1440],
        },
        "P21-R5": {"contracts": 107},
        "P21-R6": {"homes": 20, "past_due_minor": 427500},
        "P21-R7": {"independent_review": True, "review_ids": ["phase21-review"]},
    }
    gates = {
        gate: {"result": "passed", "command": f"recorded {gate}", "evidence": {**payload, "tested_revision": "candidate"}}
        for gate, payload in evidence.items()
    }
    gates["P21-R8"] = {"result": "not_run"}
    gates["P21-R9"] = {"result": "not_run"}
    return {
        "phase": 21,
        "behavior_revision": "candidate",
        "real_values_activated": False,
        "money_moved": False,
        "results": {"pytest": "call journeys passed on the clean room"},
        "commands": [
            "python scripts/phase21_clean_room.py --execute",
            "corepack yarn playwright test --config=playwright.phase21.config.js",
        ],
        "gates": gates,
    }


def test_complete_local_evidence_can_pass_before_the_pull_request():
    assert evaluate(_complete(), "local") == []


def test_a_targeted_file_is_not_acceptance():
    state = _complete()
    state["commands"] = ["python -m pytest tests/phase21/test_calls.py -q"]
    state["results"] = {"pytest": "4 passed"}
    assert any("targeted" in error for error in evaluate(state, "local"))


def test_an_older_row_security_count_is_rejected():
    state = _complete()
    state["gates"]["P21-R2"]["evidence"]["forced_rls"] = "251/251"
    assert any("row-security" in error for error in evaluate(state, "local"))


def test_a_copied_phase_20_review_is_not_a_phase_21_review():
    state = _complete()
    state["gates"]["P21-R7"]["evidence"]["review_ids"] = ["10f48972-03f0-41c6-91fc-7d296557da45"]
    assert any("independent phase 21 review" in error for error in evaluate(state, "local"))

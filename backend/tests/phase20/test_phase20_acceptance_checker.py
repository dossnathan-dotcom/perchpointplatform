"""The Phase 20 checker rejects a targeted file, an older head, and a copied review."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from phase20_acceptance import evaluate  # noqa: E402


def _complete() -> dict:
    evidence = {
        "P20-R0": {"scope": "maintenance"},
        "P20-R1": {"passed": 5, "exit_code": 0, "separate_process_worker": True},
        "P20-R2": {
            "migration_head": "0066_phase20_maintenance",
            "upgrade_from": "0065_phase19_reconciliation",
            "runtime": "false,false",
            "forced_rls": "251/251",
        },
        "P20-R3": {"thresholds_declared_first": True, "cases": 200, "bound_ms": 300, "p95_ms": 40.0},
        "P20-R4": {
            "executed": True,
            "passed": 12,
            "exit_code": 0,
            "engines": ["chromium", "firefox", "webkit"],
            "viewports": [320, 768, 1024, 1440],
        },
        "P20-R5": {"inherited": True},
        "P20-R6": {"homes": 20, "past_due_minor": 427500},
        "P20-R7": {"independent_review": True, "reviewer": "cursor-security-review", "review_ids": ["phase20-review"]},
    }
    gates = {
        gate: {"result": "passed", "command": f"recorded {gate}", "evidence": {**payload, "tested_revision": "candidate"}}
        for gate, payload in evidence.items()
    }
    gates["P20-R8"] = {"result": "not_run"}
    gates["P20-R9"] = {"result": "not_run"}
    return {
        "phase": 20,
        "behavior_revision": "candidate",
        "real_values_activated": False,
        "money_moved": False,
        "results": {"pytest": "maintenance journeys passed on the clean room"},
        "commands": [
            "python scripts/phase20_clean_room.py --execute",
            "corepack yarn playwright test --config=playwright.phase20.config.js",
        ],
        "gates": gates,
        "findings": [],
    }


def test_complete_local_evidence_can_pass_before_the_pull_request():
    assert evaluate(_complete(), "local") == []


def test_a_targeted_file_is_not_acceptance():
    state = _complete()
    state["commands"] = ["python -m pytest tests/phase20/test_maintenance.py -q"]
    state["results"] = {"pytest": "5 passed"}
    errors = evaluate(state, "local")
    assert any("targeted" in error for error in errors)


def test_an_older_head_and_copied_row_security_count_are_rejected():
    state = _complete()
    state["gates"]["P20-R2"]["evidence"]["migration_head"] = "0065_phase19_reconciliation"
    state["gates"]["P20-R2"]["evidence"]["forced_rls"] = "232/232"
    errors = evaluate(state, "local")
    assert any("phase 20 head" in error for error in errors)
    assert any("row-security count" in error for error in errors)


def test_an_in_process_worker_is_rejected():
    state = _complete()
    state["gates"]["P20-R1"]["evidence"]["separate_process_worker"] = False
    errors = evaluate(state, "local")
    assert any("in-process-only" in error for error in errors)


def test_a_copied_phase_19_review_is_not_a_phase_20_review():
    state = _complete()
    state["gates"]["P20-R7"]["evidence"]["review_ids"] = ["1769e37a-ec1f-4ba8-88cb-6ebf12bea993"]
    errors = evaluate(state, "local")
    assert any("independent phase 20 review" in error for error in errors)


def test_a_mismatched_pull_request_head_is_rejected():
    state = _complete()
    state["gates"]["P20-R8"] = {
        "result": "passed",
        "command": "gh pr checks",
        "evidence": {"pr_head": "other", "tested_revision": "candidate"},
    }
    state["pull_request"] = {"head": "candidate"}
    errors = evaluate(state, "pr")
    assert any("pull request head" in error for error in errors)

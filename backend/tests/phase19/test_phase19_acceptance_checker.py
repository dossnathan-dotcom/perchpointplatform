"""The Phase 19 checker rejects a six-test file and a copied Phase 18 review."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from phase19_acceptance import evaluate  # noqa: E402


def _complete() -> dict:
    evidence = {
        "P19-R0": {"scope": "reconciliation"},
        "P19-R1": {"passed": 6, "exit_code": 0},
        "P19-R2": {
            "migration_head": "0065_phase19_reconciliation",
            "upgrade_from": "0064_phase18_return_completion",
            "accounts_preserved": 15,
            "runtime": "false,false",
            "forced_rls": "232/232",
        },
        "P19-R3": {"thresholds_declared_first": True, "lines": 200, "bound_ms": 300, "p95_ms": 109.431},
        "P19-R4": {
            "executed": True,
            "passed": 12,
            "exit_code": 0,
            "engines": ["chromium", "firefox", "webkit"],
            "viewports": [320, 768, 1024, 1440],
        },
        "P19-R5": {"contracts": 107},
        "P19-R6": {"homes": 20, "households": 20},
        "P19-R7": {"independent_review": True, "reviewer": "cursor-security-review", "review_ids": ["phase19-review"]},
    }
    gates = {
        gate: {"result": "passed", "command": f"recorded {gate}", "evidence": {**payload, "tested_revision": "candidate"}}
        for gate, payload in evidence.items()
    }
    gates["P19-R8"] = {"result": "not_run"}
    gates["P19-R9"] = {"result": "not_run"}
    return {
        "phase": 19,
        "behavior_revision": "candidate",
        "real_values_activated": False,
        "money_moved": False,
        "phase_20_started": False,
        "results": {"pytest": "6 passed on the clean room"},
        "commands": [
            "python scripts/phase19_clean_room.py --execute",
            "corepack yarn playwright test --config=playwright.phase19.config.js",
        ],
        "gates": gates,
        "findings": [],
    }


def test_complete_local_evidence_can_pass_before_the_pull_request():
    assert evaluate(_complete(), "local") == []


def test_the_six_test_file_is_not_acceptance():
    state = _complete()
    state["commands"] = ["python -m pytest tests/phase19/test_reconciliation.py -q"]
    state["results"] = {"pytest": "6 passed in 10.80s"}
    errors = evaluate(state, "local")
    assert any("six-test" in error for error in errors)


def test_a_phase_18_row_security_count_does_not_qualify_phase_19():
    state = _complete()
    state["gates"]["P19-R2"]["evidence"]["forced_rls"] = "226/226"
    state["gates"]["P19-R2"]["evidence"]["migration_head"] = "0064_phase18_return_completion"
    errors = evaluate(state, "local")
    assert any("phase 19 head" in error for error in errors)
    assert any("row-security count" in error for error in errors)


def test_a_copied_phase_18_review_is_not_a_phase_19_review():
    state = _complete()
    state["gates"]["P19-R7"]["evidence"]["review_ids"] = ["bd9596a9-ebf6-4ea1-8ae9-38c6c386b1ac"]
    errors = evaluate(state, "local")
    assert any("separate phase 19 review" in error for error in errors)


def test_scale_without_a_declared_threshold_is_rejected():
    state = _complete()
    state["gates"]["P19-R3"]["evidence"]["thresholds_declared_first"] = False
    errors = evaluate(state, "local")
    assert any("declaring the threshold" in error for error in errors)


def test_a_mismatched_pull_request_head_is_rejected():
    state = _complete()
    state["gates"]["P19-R8"] = {
        "result": "passed",
        "command": "gh pr checks",
        "evidence": {"pr_head": "other", "tested_revision": "candidate"},
    }
    state["pull_request"] = {"head": "candidate"}
    errors = evaluate(state, "pr")
    assert any("pull request head" in error for error in errors)

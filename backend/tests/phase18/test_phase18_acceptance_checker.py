"""The Phase 18 checker rejects a targeted-test checkpoint and a Phase 17 clean room."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "scripts"))

from phase18_acceptance import evaluate  # noqa: E402


def _complete() -> dict:
    evidence = {
        "P18-R0": {"phase17_merge": "a8c494dd479c7645da0b1d95ca3d6a53fb1a9561", "scope": "digital"},
        "P18-R1": {"decisions": 49},
        "P18-R2": {"migration_head": "0064_phase18_return_completion", "runtime_role": "NOSUPERUSER", "forced_rls": True},
        "P18-R3": {"cross_organization": True},
        "P18-R4": {"resident_minor": 40000, "agency_minor": 110000},
        "P18-R5": {"cash_app": "injected", "zelle": "unavailable"},
        "P18-R6": {"program": "hcv"},
        "P18-R7": {"remittance_net_minor": 260000, "replay": "single"},
        "P18-R8": {"reservation": True},
        "P18-R9": {"return_linked": True},
        "P18-R10": {"worker": "process"},
        "P18-R11": {"personas": ["resident", "operations", "owner"]},
        "P18-R12": {"executed": True, "engines": ["chromium", "firefox", "webkit"], "viewports": [320, 768, 1024, 1440]},
        "P18-R13": {"households": 20, "homes": 20},
        "P18-R14": {"clean_room_head": "0064_phase18_return_completion", "scale": True},
        "P18-R15": {"contracts": True},
        "P18-R16": {"independent_review": True, "reviewer": "cursor-security-review"},
    }
    gates = {
        gate: {"result": "passed", "command": f"recorded {gate}", "evidence": {**payload, "tested_revision": "candidate"}}
        for gate, payload in evidence.items()
    }
    gates["P18-R17"] = {"result": "not_run"}
    gates["P18-R18"] = {"result": "not_run"}
    return {
        "behavior_revision": "candidate",
        "real_values_activated": False,
        "money_moved": False,
        "phase_19_started": False,
        "results": {"pytest": "candidate suite"},
        "commands": ["python -m pytest tests/phase18 -n 0", "playwright", "phase18_clean_room"],
        "gates": gates,
        "findings": [],
    }


def test_complete_local_evidence_can_pass_before_the_pull_request():
    assert evaluate(_complete(), "local") == []


def test_the_18_test_checkpoint_is_not_acceptance():
    state = {
        "real_values_activated": False,
        "money_moved": False,
        "phase_19_started": False,
        "commands": ["python -m pytest tests/phase18/test_assistance.py -n 0 --tb=line -q"],
        "results": {"pytest": "18 passed in 89.73s"},
        "gates": {gate: {"result": "passed", "command": "pytest", "evidence": {"tested_revision": "candidate"}} for gate in (f"P18-R{index}" for index in range(17))},
    }
    errors = evaluate(state, "local")
    assert any("targeted assistance checkpoint" in error for error in errors)
    assert any("browser matrix" in error for error in errors)
    assert any("independent review" in error for error in errors)


def test_a_phase_17_clean_room_does_not_qualify_phase_18():
    state = _complete()
    state["gates"]["P18-R2"]["evidence"]["migration_head"] = "0060_phase17_grant_accept"
    state["gates"]["P18-R14"]["evidence"]["clean_room_head"] = "0060_phase17_grant_accept"
    errors = evaluate(state, "local")
    assert any("stopped before the phase 18 head" in error for error in errors)
    assert any("phase 17 head" in error for error in errors)


def test_an_invariant_script_is_not_independent_review():
    state = _complete()
    state["gates"]["P18-R16"]["evidence"]["reviewer"] = "phase18-invariant-review"
    errors = evaluate(state, "local")
    assert any("independent review" in error for error in errors)


def test_an_in_process_worker_is_not_process_proof():
    state = _complete()
    state["gates"]["P18-R10"]["evidence"]["worker"] = "in_process"
    errors = evaluate(state, "local")
    assert any("separate worker process" in error for error in errors)


def test_a_mismatched_pull_request_head_is_rejected():
    state = _complete()
    state["gates"]["P18-R17"] = {
        "result": "passed",
        "command": "gh pr checks",
        "evidence": {"pr_head": "other", "tested_revision": "candidate"},
    }
    state["pull_request"] = {"head": "candidate"}
    errors = evaluate(state, "pr")
    assert any("pull request head" in error for error in errors)

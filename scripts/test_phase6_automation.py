"""Unit tests for Phase 6 evidence/checker automation (no Docker required)."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import phase6_clean_room
from phase6_acceptance import CLEAN_ROOM_STEPS
from phase6_evidence_schema import (
    SCHEMA_VERSION,
    EvidenceError,
    load_json,
    sha256_text,
    validate_executions,
    validate_provenance,
)
from validate_phase6_answers import validate_substance


def provenance(kind: str = "sample") -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "kind": kind,
        "commit": "a" * 40,
        "command": "python proof.py",
        "timestamp": "2026-10-04T12:00:00+00:00",
        "exit_code": 0,
        "totals": {"total": 2, "passed": 2, "failed": 0, "skipped": 0},
    }


class EvidenceSchemaTests(unittest.TestCase):
    def test_clean_room_driver_names_every_required_step(self) -> None:
        source = (Path(__file__).parent / "phase6_clean_room.py").read_text(encoding="utf-8")
        for step in CLEAN_ROOM_STEPS:
            self.assertIn(f'"{step}"', source)

    def test_full_backend_pauses_the_live_outbox_worker(self) -> None:
        source = (Path(__file__).parent / "phase6_clean_room.py").read_text(encoding="utf-8")
        full = source.split('"full-backend"', 1)[1].split("driver.step(", 1)[0]
        stop = full.index('"stop", "worker"')
        pytest_call = full.index("_full_pytest()")
        start = full.index('"start", "worker"')
        self.assertLess(stop, pytest_call)
        self.assertLess(pytest_call, start)

    def test_provenance_rejects_skip_and_stale_commit(self) -> None:
        report = provenance()
        report["totals"]["passed"] = 1
        report["totals"]["skipped"] = 1
        errors = validate_provenance(report, kind="sample", commit="b" * 40)
        self.assertIn("obsolete commit", errors)
        self.assertIn("required skips", errors)

    def test_execution_requires_command_digest_output_and_every_step(self) -> None:
        report = {
            "executions": [
                {
                    "step": CLEAN_ROOM_STEPS[0],
                    "command": "docker compose config",
                    "started_at": "2026-10-04T12:00:00+00:00",
                    "finished_at": "2026-10-04T12:00:01+00:00",
                    "exit_code": 0,
                    "output_sha256": sha256_text("ok"),
                    "output_bytes": 2,
                }
            ]
        }
        errors = validate_executions(report, CLEAN_ROOM_STEPS)
        self.assertIn(f"missing execution:{CLEAN_ROOM_STEPS[1]}", errors)

    def test_load_json_rejects_non_object(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "report.json"
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(EvidenceError):
                load_json(path)

    def test_clean_room_failure_never_emits_success_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            reports = Path(directory)
            success = reports / "clean-room.json"
            success.write_text('{"stale": true}', encoding="utf-8")
            with (
                patch.object(phase6_clean_room, "REPORTS", reports),
                patch.object(
                    phase6_clean_room,
                    "source_provenance",
                    return_value={
                        "commit": "a" * 40,
                        "tree_hash": "b" * 40,
                        "source_clean": False,
                    },
                ),
                patch.object(phase6_clean_room.Driver, "step", side_effect=phase6_clean_room.StepFailure("boom")),
                patch.object(phase6_clean_room.subprocess, "run"),
                self.assertRaises(phase6_clean_room.StepFailure),
            ):
                phase6_clean_room.run()
            self.assertFalse(success.exists())
            self.assertTrue((reports / "clean-room.failed.json").exists())


class AnswerCompletenessTests(unittest.TestCase):
    def test_placeholders_duplicates_and_absent_targets_fail(self) -> None:
        answers = {1: "TBD.", 2: "This is a sufficiently long complete decision.", 3: "This is a sufficiently long complete decision."}
        trace = {1: "missing.py", 2: "docs/only.md", 3: "backend/missing.py"}
        errors = validate_substance(answers, trace)
        self.assertTrue(any("not substantive" in error for error in errors))
        self.assertTrue(any("duplicate decision" in error for error in errors))
        self.assertTrue(any("target absent" in error for error in errors))
        self.assertTrue(any("no implementation trace" in error for error in errors))


if __name__ == "__main__":
    unittest.main()

"""Regression tests for the forward-compatible Phase 6 migration gate."""
from __future__ import annotations

import unittest
from pathlib import Path

import phase6_migration_lineage as lineage


PHASE6 = "0031_phase6_authz_remediation"
PHASE7_PUBLICATION = "0034_phase7_publication_jobs"
PHASE7_VISIBILITY = "0035_phase7_property_visibility"


def chain(*revisions: str) -> dict[str, str | None]:
    graph: dict[str, str | None] = {}
    parent = None
    for revision in revisions:
        graph[revision] = parent
        parent = revision
    return graph


class MigrationLineageTests(unittest.TestCase):
    def test_current_head_descends_from_phase6(self) -> None:
        result = lineage.assess(
            chain("0011_phase5_hold_guard", PHASE6, PHASE7_PUBLICATION, PHASE7_VISIBILITY),
            PHASE7_VISIBILITY,
        )
        self.assertEqual(result["ancestry"], "confirmed")
        self.assertEqual(result["reached_head"], PHASE7_VISIBILITY)
        self.assertEqual(result["current_head"], PHASE7_VISIBILITY)
        self.assertEqual(result["required_revision"], PHASE6)

    def test_hypothetical_descendant_after_0034_passes(self) -> None:
        later = "0036_later_phase_example"
        result = lineage.assess(
            chain(PHASE6, PHASE7_PUBLICATION, PHASE7_VISIBILITY, later),
            later,
        )
        self.assertEqual(result["reached_head"], later)
        self.assertEqual(result["required_revision"], PHASE6)
        self.assertNotEqual(result["reached_head"], PHASE7_PUBLICATION)

    def test_missing_phase6_revision_fails(self) -> None:
        with self.assertRaises(lineage.LineageError) as raised:
            lineage.assess(chain("0011_phase5_hold_guard", PHASE7_PUBLICATION), PHASE7_PUBLICATION)
        self.assertIn(PHASE6, str(raised.exception))

    def test_migration_that_stops_before_head_fails(self) -> None:
        with self.assertRaises(lineage.LineageError) as raised:
            lineage.assess(chain(PHASE6, PHASE7_VISIBILITY), PHASE6)
        self.assertIn(PHASE7_VISIBILITY, str(raised.exception))

    def test_unexpected_multiple_heads_fail(self) -> None:
        graph = {
            PHASE6: None,
            PHASE7_VISIBILITY: PHASE6,
            "0099_unexpected_side": PHASE6,
        }
        with self.assertRaises(lineage.LineageError) as raised:
            lineage.assess(graph, PHASE7_VISIBILITY)
        self.assertIn("exactly one head", str(raised.exception))

    def test_unexpected_branch_fails(self) -> None:
        graph = {
            PHASE6: None,
            "0099_unexpected_side": None,
            PHASE7_VISIBILITY: (PHASE6, "0099_unexpected_side"),
        }
        with self.assertRaises(lineage.LineageError) as raised:
            lineage.assess(graph, PHASE7_VISIBILITY)
        self.assertIn("unexpected branch", str(raised.exception))

    def test_repository_graph_keeps_phase6_under_one_head(self) -> None:
        graph = lineage.load_repository_graph()
        heads = sorted(revision for revision, parent in graph.items() if revision not in set(graph.values()))
        self.assertEqual(len(heads), 1)
        result = lineage.assess(graph, heads[0])
        self.assertEqual(result["ancestry"], "confirmed")
        self.assertEqual(result["required_revision"], PHASE6)
        self.assertNotEqual(result["reached_head"], PHASE6)
        self.assertIn(PHASE7_PUBLICATION, graph)
        self.assertEqual(graph[PHASE7_VISIBILITY], PHASE7_PUBLICATION)
        self.assertEqual(graph["0036_phase8_availability"], PHASE7_VISIBILITY)
        self.assertEqual(graph["0037_phase9_discovery"], "0036_phase8_availability")
        self.assertEqual(graph["0038_phase10_inquiry"], "0037_phase9_discovery")
        self.assertEqual(graph["0039_phase11_showing"], "0038_phase10_inquiry")
        self.assertEqual(graph["0040_phase12_application"], "0039_phase11_showing")
        self.assertEqual(graph["0041_phase13_screening"], "0040_phase12_application")

    def test_clean_room_executes_upgrade_and_graph_check(self) -> None:
        source = (Path(__file__).parent / "phase6_clean_room.py").read_text(encoding="utf-8")
        self.assertEqual(source.count('"alembic", "upgrade", "head"'), 2)
        self.assertIn("phase6_migration_lineage.py", source)
        self.assertEqual(source.count("--database-url"), 1)
        self.assertIn('"migrate",\n        "python", "scripts/phase6_migration_lineage.py"', source)
        self.assertEqual(source.count("_lineage("), 3)
        self.assertNotIn('require="0031_phase6_authz_remediation"', source)
        self.assertNotIn('require="0034_phase7_publication_jobs"', source)
        self.assertNotIn('require="0035_phase7_property_visibility"', source)
        self.assertEqual(source.count(f'require="{lineage.CONFIRMED}"'), 2)


if __name__ == "__main__":
    unittest.main()

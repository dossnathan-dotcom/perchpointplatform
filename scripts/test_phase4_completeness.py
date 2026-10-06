"""Phase 4 destinations stay required after later public-surface additions."""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import validate_phase4_completeness as completeness


class Phase4CompletenessTests(unittest.TestCase):
    def test_historical_labels_remain_required(self) -> None:
        required = completeness.required_destinations(
            completeness.PHASE4_SURFACES,
            completeness.PHASE7_SURFACES,
        )
        flattened = [label for labels in required.values() for label in labels]
        for label in (
            "Rentals", "Commercial", "About HawkVision", "Contact", "Apply",
            "Resident Login", "Staff Login",
        ):
            self.assertIn(label, flattened)
        self.assertIn("Commercial", required["frontend/src/components/Footer.jsx"])
        self.assertIn("About HawkVision", required["frontend/src/components/AboutHawkVision.jsx"])
        self.assertNotIn("Commercial", required["frontend/src/components/Navbar.jsx"])

    def test_later_phase_label_does_not_erase_the_baseline(self) -> None:
        later = {"frontend/src/components/Navbar.jsx": ["Phase Eight Destination"]}
        required = completeness.required_destinations(completeness.PHASE4_SURFACES, later)
        self.assertIn("Phase Eight Destination", required["frontend/src/components/Navbar.jsx"])
        self.assertIn("Rentals", required["frontend/src/components/Navbar.jsx"])
        self.assertIn("Commercial", required["frontend/src/components/Footer.jsx"])
        self.assertIn("About HawkVision", required["frontend/src/components/AboutHawkVision.jsx"])

    def test_repository_surfaces_satisfy_the_inventory(self) -> None:
        gaps = completeness.destination_gaps(
            completeness.ROOT,
            completeness.required_destinations(
                completeness.PHASE4_SURFACES,
                completeness.PHASE7_SURFACES,
            ),
        )
        self.assertEqual(gaps, [])

    def test_missing_historical_destination_fails(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            navbar = root / "Navbar.jsx"
            footer = root / "Footer.jsx"
            about = root / "About.jsx"
            navbar.write_text('"Rentals"', encoding="utf-8")
            footer.write_text("<Link>Other</Link>", encoding="utf-8")
            about.write_text(">About HawkVision<", encoding="utf-8")
            gaps = completeness.destination_gaps(
                root,
                {
                    "Navbar.jsx": ["Rentals"],
                    "Footer.jsx": ["Commercial"],
                    "About.jsx": ["About HawkVision"],
                },
            )
        self.assertEqual(gaps, ["Footer.jsx missing Commercial"])

    def test_moved_historical_destination_passes_on_its_owning_surface(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "Navbar.jsx").write_text('"Rentals" "Home"', encoding="utf-8")
            (root / "Footer.jsx").write_text(">Commercial<", encoding="utf-8")
            (root / "About.jsx").write_text(">About HawkVision<", encoding="utf-8")
            gaps = completeness.destination_gaps(
                root,
                {
                    "Navbar.jsx": ["Rentals", "Home"],
                    "Footer.jsx": ["Commercial"],
                    "About.jsx": ["About HawkVision"],
                },
            )
        self.assertEqual(gaps, [])


if __name__ == "__main__":
    unittest.main()

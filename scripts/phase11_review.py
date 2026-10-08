"""Independent Phase 11 invariant review. Fails on later-phase, live-provider, or self-guided drift."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0039_phase11_showing_calendar.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0039_phase11_showing_calendar.py").read_text(encoding="utf-8")
    module = (ROOT / "backend/perchpoint/phase11_scheduling.py").read_text(encoding="utf-8")
    if "0039_phase11_showing" not in revision or 'down_revision = "0038_phase10_inquiry"' not in revision:
        findings.append({"severity": "high", "id": "lineage", "detail": "0039 is not a child of 0038"})
    if "FORCE ROW LEVEL SECURITY" not in sql or "showing_occupancy_no_overlap" not in sql:
        findings.append({"severity": "high", "id": "rls", "detail": "showing row security or overlap exclusion is missing"})
    if "self_guided" not in sql or "lockbox" not in sql:
        findings.append({"severity": "high", "id": "access", "detail": "self-guided and lockbox requests are not rejected"})
    if "def create_application" in module or "zillow" in module.lower():
        findings.append({"severity": "high", "id": "boundary", "detail": "application creation or marketplace scheduling is present"})
    if list(ROOT.glob("backend/perchpoint/phase12*.py")):
        findings.append({"severity": "high", "id": "phase12", "detail": "a Phase 12 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase11-independent-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

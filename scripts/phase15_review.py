"""Independent Phase 15 invariant review. Fails on later-domain writes or an unmarked sample lease."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0043_phase15_resident_portal.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0043_phase15_resident_portal.py").read_text(encoding="utf-8")
    module = (ROOT / "backend/perchpoint/phase15_portal.py").read_text(encoding="utf-8")
    if "0043_phase15_resident_portal" not in revision or 'down_revision = "0042_phase14_lease"' not in revision:
        findings.append({"severity": "high", "id": "lineage", "detail": "0043 is not a child of 0042"})
    if "FORCE ROW LEVEL SECURITY" not in sql or "real_values_activated = false" not in sql:
        findings.append({"severity": "high", "id": "security", "detail": "forced row security or manifest guard is missing"})
    if "SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION" not in module or "SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION" not in sql:
        findings.append({"severity": "high", "id": "sample", "detail": "the sample lease marker is missing"})
    lowered = module.lower()
    if "stripe" in lowered or "docusign" in lowered or "twilio" in lowered:
        findings.append({"severity": "high", "id": "provider", "detail": "a live provider action is present"})
    if "ledger_postings" in sql or "maintenance_work_orders" in sql or "message_threads" in sql:
        findings.append({"severity": "high", "id": "boundary", "detail": "a later-domain table is present"})
    if list(ROOT.glob("backend/perchpoint/phase16*.py")):
        findings.append({"severity": "high", "id": "phase16", "detail": "a Phase 16 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase15-independent-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

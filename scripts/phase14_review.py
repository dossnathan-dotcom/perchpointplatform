"""Independent Phase 14 invariant review. Fails on live providers, ledgers, or portal behavior."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0042_phase14_lease.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0042_phase14_lease.py").read_text(encoding="utf-8")
    module = (ROOT / "backend/perchpoint/phase14_lease.py").read_text(encoding="utf-8")
    if "0042_phase14_lease" not in revision or 'down_revision = "0041_phase13_screening"' not in revision:
        findings.append({"severity": "high", "id": "lineage", "detail": "0042 is not a child of 0041"})
    if "FORCE ROW LEVEL SECURITY" not in sql or "CHECK (human_confirmed)" not in sql:
        findings.append({"severity": "high", "id": "approval", "detail": "row security or human confirmation is missing"})
    if "ledger_postings" in sql or "resident_portal" in sql:
        findings.append({"severity": "high", "id": "boundary", "detail": "a ledger or resident portal table is present"})
    lowered = module.lower()
    if "docusign" in lowered or "stripe" in lowered or "create_payment" in lowered:
        findings.append({"severity": "high", "id": "provider", "detail": "a live provider action is present"})
    if list(ROOT.glob("backend/perchpoint/phase15*.py")):
        findings.append({"severity": "high", "id": "phase15", "detail": "a Phase 15 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase14-independent-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

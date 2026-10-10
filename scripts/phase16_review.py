"""Independent Phase 16 invariant review. Fails on live money movement or a formal ledger claim."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0044_phase16_ledger.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0044_phase16_ledger.py").read_text(encoding="utf-8")
    module = (ROOT / "backend/perchpoint/phase16_ledger.py").read_text(encoding="utf-8")
    if "0044_phase16_ledger" not in revision or 'down_revision = "0043_phase15_resident_portal"' not in revision:
        findings.append({"severity": "high", "id": "lineage", "detail": "0044 is not a child of 0043"})
    if "FORCE ROW LEVEL SECURITY" not in sql or "real_values_activated = false" not in sql:
        findings.append({"severity": "high", "id": "security", "detail": "forced row security or manifest guard is missing"})
    if "SYNTHETIC OPERATIONAL STATEMENT" not in module or "SYNTHETIC OPERATIONAL STATEMENT" not in sql:
        findings.append({"severity": "high", "id": "statement", "detail": "the synthetic statement marker is missing"})
    if "money_moved = false" not in sql:
        findings.append({"severity": "high", "id": "money", "detail": "posted transactions are not constrained against money movement"})
    lowered = module.lower()
    if "stripe" in lowered or "docusign" in lowered or "twilio" in lowered:
        findings.append({"severity": "high", "id": "provider", "detail": "a live provider action is present"})
    if "maintenance_work_orders" in sql or "message_threads" in sql:
        findings.append({"severity": "high", "id": "boundary", "detail": "a later-domain table is present"})
    if list(ROOT.glob("backend/perchpoint/phase17*.py")):
        findings.append({"severity": "high", "id": "phase17", "detail": "a Phase 17 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase16-independent-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Independent Phase 12 invariant review. Fails on screening, lease, payment, or marketplace drift."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0040_phase12_application.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0040_phase12_application.py").read_text(encoding="utf-8")
    module = (ROOT / "backend/perchpoint/phase12_applications.py").read_text(encoding="utf-8")
    if "0040_phase12_application" not in revision or 'down_revision = "0039_phase11_showing"' not in revision:
        findings.append({"severity": "high", "id": "lineage", "detail": "0040 is not a child of 0039"})
    if "FORCE ROW LEVEL SECURITY" not in sql or "fee_state = 'not_collected'" not in sql:
        findings.append({"severity": "high", "id": "rls", "detail": "application row security or the unpaid fee constraint is missing"})
    if "criminal_history" not in sql or "credit_score" not in sql:
        findings.append({"severity": "high", "id": "screening", "detail": "screening questions are not rejected"})
    lowered = module.lower()
    if "zillow" in lowered or "stripe" in lowered or "create_lease" in lowered:
        findings.append({"severity": "high", "id": "boundary", "detail": "a marketplace, payment, or lease action is present"})
    if list(ROOT.glob("backend/perchpoint/phase13*.py")):
        findings.append({"severity": "high", "id": "phase13", "detail": "a Phase 13 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase12-independent-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

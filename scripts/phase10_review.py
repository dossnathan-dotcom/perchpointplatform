"""Independent Phase 10 invariant review. Fails on later-phase or marketplace drift."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0038_phase10_inquiry_crm.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0038_phase10_inquiry_crm.py").read_text(encoding="utf-8")
    module = (ROOT / "backend/perchpoint/phase10_crm.py").read_text(encoding="utf-8")
    routes = (ROOT / "backend/perchpoint/phase10_routes.py").read_text(encoding="utf-8")
    if "0038_phase10_inquiry" not in revision or "0037_phase9_discovery" not in revision:
        findings.append({"severity": "high", "id": "lineage", "detail": "0038 is not a child of 0037"})
    if "FORCE ROW LEVEL SECURITY" not in sql or "capture_leasing_inquiry" not in sql:
        findings.append({"severity": "high", "id": "rls", "detail": "inquiry row security or capture function is missing"})
    if "lead_score" not in sql or "tenant_quality" not in sql:
        findings.append({"severity": "high", "id": "scoring", "detail": "prohibited score fields are not rejected"})
    if "def schedule_showing" in module or "def create_application" in module or "zillow" in routes.lower():
        findings.append({"severity": "high", "id": "boundary", "detail": "marketplace, showing scheduling, or application creation is present"})
    if list(ROOT.glob("backend/perchpoint/phase11*.py")):
        findings.append({"severity": "high", "id": "phase11", "detail": "a Phase 11 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase10-independent-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

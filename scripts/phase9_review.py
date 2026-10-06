"""Independent Phase 9 invariant review. Fails on syndication or policy drift."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0037_phase9_listing_discovery.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0037_phase9_listing_discovery.py").read_text(encoding="utf-8")
    module = (ROOT / "backend/perchpoint/phase9_discovery.py").read_text(encoding="utf-8")
    routes = (ROOT / "backend/perchpoint/phase9_routes.py").read_text(encoding="utf-8")
    if "0037_phase9_discovery" not in revision or "0036_phase8_availability" not in revision:
        findings.append({"severity": "high", "id": "lineage", "detail": "0037 is not a child of 0036"})
    if "FORCE ROW LEVEL SECURITY" not in sql or "search_discovery" not in sql:
        findings.append({"severity": "high", "id": "rls", "detail": "discovery row security or search function is missing"})
    if "zillow" not in module.lower() or "channel_disabled" not in module:
        findings.append({"severity": "high", "id": "syndication", "detail": "external syndication is not explicitly rejected"})
    if "inquiry" in routes.lower() and "create_inquiry" in routes:
        findings.append({"severity": "high", "id": "phase10", "detail": "inquiry creation is present"})
    if list(ROOT.glob("backend/perchpoint/phase10*.py")):
        findings.append({"severity": "high", "id": "phase10-module", "detail": "a Phase 10 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase9-independent-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

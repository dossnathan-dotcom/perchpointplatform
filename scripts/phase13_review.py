"""Independent Phase 13 invariant review. Fails on live providers, leases, or automated denial."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0041_phase13_screening.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0041_phase13_screening.py").read_text(encoding="utf-8")
    module = (ROOT / "backend/perchpoint/phase13_screening.py").read_text(encoding="utf-8")
    if "0041_phase13_screening" not in revision or 'down_revision = "0040_phase12_application"' not in revision:
        findings.append({"severity": "high", "id": "lineage", "detail": "0041 is not a child of 0040"})
    if "FORCE ROW LEVEL SECURITY" not in sql or "CHECK (human_confirmed)" not in sql:
        findings.append({"severity": "high", "id": "decision", "detail": "row security or human confirmation is missing"})
    if "product IN ('credit', 'income', 'rental')" not in sql:
        findings.append({"severity": "high", "id": "criminal", "detail": "criminal products are not excluded from orders"})
    lowered = module.lower()
    if "checkr" in lowered or "experian" in lowered or "transunion" in lowered or "create_lease" in lowered:
        findings.append({"severity": "high", "id": "provider", "detail": "a live provider or lease action is present"})
    if list(ROOT.glob("backend/perchpoint/phase14*.py")):
        findings.append({"severity": "high", "id": "phase14", "detail": "a Phase 14 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase13-independent-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

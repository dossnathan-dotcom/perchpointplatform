"""Independent Phase 7 invariant review. Fails on critical scope or policy drift."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    policy = (ROOT / "backend/alembic/sql/0035_phase7_property_visibility.sql").read_text(encoding="utf-8")
    if "worker_assignment_allows" not in policy:
        findings.append({"severity": "high", "id": "property-visibility", "detail": "assignment predicate missing"})
    phase8 = list(ROOT.glob("backend/perchpoint/phase8*.py"))
    if phase8:
        findings.append({"severity": "high", "id": "phase8", "detail": "phase 8 module is present"})
    routes = (ROOT / "backend/perchpoint/routes.py").read_text(encoding="utf-8")
    if 'path.startswith("/content")' not in routes:
        findings.append({"severity": "high", "id": "content-route", "detail": "content routes are unclassified"})
    bootstrap = (ROOT / "backend/perchpoint/bootstrap.py").read_text(encoding="utf-8")
    if "perchpoint_runtime" not in bootstrap or "NOBYPASSRLS" not in bootstrap:
        findings.append({"severity": "high", "id": "runtime-role", "detail": "runtime role is not restricted"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings)}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

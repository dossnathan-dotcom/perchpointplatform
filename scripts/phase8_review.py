"""Independent Phase 8 invariant review. Fails on critical scope or policy drift."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    sql = (ROOT / "backend/alembic/sql/0036_phase8_property_availability.sql").read_text(encoding="utf-8")
    revision = (ROOT / "backend/alembic/versions/0036_phase8_property_availability.py").read_text(encoding="utf-8")
    portfolio = (ROOT / "backend/perchpoint/phase8_portfolio.py").read_text(encoding="utf-8")
    routes = (ROOT / "backend/perchpoint/phase8_routes.py").read_text(encoding="utf-8")
    bootstrap = (ROOT / "backend/perchpoint/bootstrap.py").read_text(encoding="utf-8")
    if "0036_phase8_availability" not in revision or "0035_phase7_property_visibility" not in revision:
        findings.append({"severity": "high", "id": "migration-lineage", "detail": "0036 is not a child of 0035"})
    if len("0036_phase8_availability") > 32:
        findings.append({"severity": "high", "id": "revision-width", "detail": "revision id exceeds varchar(32)"})
    for table in (
        "property_address_records",
        "asking_prices",
        "listing_media_assets",
        "listing_snapshots",
        "availability_holds",
    ):
        if f"ALTER TABLE {table} FORCE ROW LEVEL SECURITY" not in sql and "FORCE ROW LEVEL SECURITY" not in sql:
            findings.append({"severity": "high", "id": f"rls-{table}", "detail": "forced row security is missing"})
            break
    if "published_listing_snapshot" not in sql or "published_listing_snapshot(text)" not in bootstrap:
        findings.append({"severity": "high", "id": "public-snapshot", "detail": "public snapshot definer is missing"})
    if "organization_id" not in sql or "access_code" not in sql:
        findings.append({"severity": "high", "id": "public-minimization", "detail": "snapshot payload check is missing"})
    if 'role != "owner"' not in portfolio and "role != 'owner'" not in portfolio:
        findings.append({"severity": "high", "id": "owner-pricing", "detail": "material pricing is not owner-reserved"})
    lowered = (routes + portfolio).lower()
    for token in ("zillow", "facebook", "mls", "syndication"):
        if token in lowered:
            findings.append({"severity": "high", "id": "phase9-leak", "detail": f"{token} appears in Phase 8 routes"})
    if list(ROOT.glob("backend/perchpoint/phase9*.py")):
        findings.append({"severity": "high", "id": "phase9-module", "detail": "a Phase 9 module is present"})
    if "NOBYPASSRLS" not in bootstrap:
        findings.append({"severity": "high", "id": "runtime-role", "detail": "runtime role is not restricted"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "p7_m1": "resolved-by-phase8-media-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

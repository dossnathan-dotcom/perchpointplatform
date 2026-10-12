"""Invariant review for the Phase 17 payment tree.

This checks the current files for the boundaries the phase must keep.
It is not a pull-request review and it does not grant acceptance.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    findings = []
    payments = (ROOT / "backend/perchpoint/phase17_payments.py").read_text(encoding="utf-8")
    worker = (ROOT / "backend/perchpoint/phase17_worker.py").read_text(encoding="utf-8")
    merchant = (ROOT / "backend/alembic/sql/0045_phase17_payments.sql").read_text(encoding="utf-8")
    head = (ROOT / "backend/alembic/versions/0060_phase17_grant_accept.py").read_text(encoding="utf-8")
    grant_owner = (ROOT / "backend/alembic/versions/0059_phase17_grant_owner.py").read_text(encoding="utf-8")
    scope = (ROOT / "backend/alembic/versions/0058_phase17_tenancy_scope.py").read_text(encoding="utf-8")
    previous_head = (ROOT / "backend/alembic/versions/0057_phase17_autopay_due.py").read_text(encoding="utf-8")
    previous = (ROOT / "backend/alembic/versions/0056_phase17_worker_scope.py").read_text(encoding="utf-8")
    inbox = (ROOT / "backend/alembic/versions/0055_phase17_worker_inbox.py").read_text(encoding="utf-8")
    if 'down_revision = "0059_phase17_grant_owner"' not in head:
        findings.append({"severity": "high", "id": "lineage", "detail": "0060 is not a child of 0059"})
    if 'down_revision = "0058_phase17_tenancy_scope"' not in grant_owner:
        findings.append({"severity": "high", "id": "lineage", "detail": "0059 is not a child of 0058"})
    if 'down_revision = "0057_phase17_autopay_due"' not in scope:
        findings.append({"severity": "high", "id": "lineage", "detail": "0058 is not a child of 0057"})
    if 'down_revision = "0056_phase17_worker_scope"' not in previous_head:
        findings.append({"severity": "high", "id": "lineage", "detail": "0057 is not a child of 0056"})
    if 'down_revision = "0055_phase17_worker_inbox"' not in previous:
        findings.append({"severity": "high", "id": "lineage", "detail": "0056 is not a child of 0055"})
    if 'down_revision = "0054_phase17_worker_claim"' not in inbox:
        findings.append({"severity": "high", "id": "lineage", "detail": "0055 is not a child of 0054"})
    if "PHASE2_ADMIN_URL" not in worker or "PHASE17_RESTRICTED_WORKER" not in worker:
        findings.append({"severity": "high", "id": "worker-credential", "detail": "the worker process still keeps the admin database URL"})
    inbox_start = payments.find("def process_provider_inbox")
    inbox_body = payments[inbox_start:payments.find("\ndef ", inbox_start + 1)]
    if "application_admin_connection" in inbox_body:
        findings.append({"severity": "high", "id": "inbox-admin", "detail": "provider inbox posting still opens the superuser connection"})
    if "store_provider_event" not in payments:
        findings.append({"severity": "high", "id": "event-store", "detail": "provider events are not stored through the restricted function"})
    if "real_values_activated = false" not in merchant or "live_enabled = false" not in merchant:
        findings.append({"severity": "high", "id": "activation", "detail": "the merchant row does not keep live collection closed"})
    if "money_moved = false" not in merchant:
        findings.append({"severity": "high", "id": "money", "detail": "payment journal inserts are not constrained against money movement"})
    if list(ROOT.glob("backend/perchpoint/phase18*.py")):
        findings.append({"severity": "high", "id": "phase18", "detail": "a Phase 18 module is present"})
    print(json.dumps({"findings": findings, "critical_or_high": len(findings), "reviewer": "phase17-invariant-review"}, indent=2))
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())

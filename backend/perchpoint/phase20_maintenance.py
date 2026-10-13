"""Phase 20 maintenance intake and field handoffs.

Cases stay on maintenance_cases. These commands record operational facts.
They do not move money, post journals, or collect real locations.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .db import runtime_transaction
from .settings import Settings

SAFETY = (
    "If you are in immediate danger, leave the area and contact local emergency services "
    "(911 in the US). Do not attempt electrical, gas, or structural repairs. "
    "This application does not dispatch help."
)
PROPERTY_ZONE = ZoneInfo("America/New_York")
ROUTINE_LIMIT = 120_000
EMERGENCY_LIMIT = 250_000
MAX_UPLOAD = 8_000_000


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _role(connection) -> str:
    role = connection.execute(
        text(
            "SELECT role_name FROM memberships WHERE account_id = perchpoint.current_actor() "
            "AND organization_id = perchpoint.current_org() AND (ended_at IS NULL OR ended_at > now()) "
            "ORDER BY effective_at DESC LIMIT 1"
        )
    ).scalar()
    return str(role or "")


def _account_for_role(connection, role: str):
    return connection.execute(
        text(
            "SELECT account_id FROM memberships WHERE organization_id = perchpoint.current_org() "
            "AND role_name = :role AND (ended_at IS NULL OR ended_at > now()) ORDER BY effective_at LIMIT 1"
        ),
        {"role": role},
    ).scalar()


def _reference(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8].upper()}"


def _fingerprint(parts: list) -> str:
    return hashlib.sha256("|".join(str(part) for part in parts).encode()).hexdigest()


def _replay(connection, key: str, fingerprint: str) -> dict | None:
    existing = connection.execute(
        text(
            "SELECT fingerprint, public_reference FROM maintenance_commands "
            "WHERE idempotency_key = :key AND actor_id = perchpoint.current_actor()"
        ),
        {"key": key},
    ).first()
    if existing is None:
        return None
    if existing.fingerprint != fingerprint:
        raise CommandError(409, "conflict", "That maintenance request changed and was not accepted.", False)
    return {"accepted": True, "reference": existing.public_reference, "replayed": True}


def _remember(connection, organization, key: str, fingerprint: str, reference: str) -> None:
    connection.execute(
        text(
            "INSERT INTO maintenance_commands (organization_id, actor_id, idempotency_key, fingerprint, public_reference) "
            "VALUES (:org, perchpoint.current_actor(), :key, :fingerprint, :reference)"
        ),
        {"org": organization, "key": key, "fingerprint": fingerprint, "reference": reference},
    )


def _report(connection, reference: str) -> dict:
    row = connection.execute(
        text("SELECT * FROM maintenance_reports WHERE public_reference = :reference"),
        {"reference": reference},
    ).mappings().first()
    if row is None:
        raise CommandError(404, "missing", "That maintenance case was not found.", False)
    return dict(row)


def _journals(connection) -> int:
    return int(connection.execute(text("SELECT count(*) FROM journal_transactions")).scalar_one())


def _severity(urgency: dict) -> tuple[str, str | None]:
    emergency = bool(urgency.get("immediate_danger") or urgency.get("human_emergency"))
    if emergency:
        return "emergency", SAFETY
    if urgency.get("essential_service") or urgency.get("continuing_damage") or urgency.get("worsening"):
        return "urgent", None
    return "routine", None


def _due(severity: str, reported_at: datetime) -> datetime:
    minutes = {"emergency": 5, "urgent": 60, "routine": 1440}[severity]
    return reported_at + timedelta(minutes=minutes)


def _after_hours(moment: datetime) -> bool:
    local = moment.astimezone(PROPERTY_ZONE)
    return local.weekday() >= 5 or local.hour < 9 or local.hour >= 17


def _queue_escalation(connection, organization, case_id, severity: str, reported_at: datetime, fail_first: bool) -> None:
    if severity != "emergency" and not _after_hours(reported_at):
        return
    chain = ["technician", "owner", "owner"] if _after_hours(reported_at) or severity == "emergency" else ["operations_manager"]
    step = 0
    role = chain[0]
    connection.execute(
        text(
            "INSERT INTO maintenance_escalations (organization_id, id, case_id, step, recipient_role, state, fail_delivery, dedup_key) "
            "VALUES (:org, :id, :case, :step, :role, 'queued', :fail, :dedup)"
        ),
        {
            "org": organization,
            "id": uuid4(),
            "case": case_id,
            "step": step,
            "role": role,
            "fail": bool(fail_first and os.environ.get("PHASE3_ENVIRONMENT", "local") in {"local", "test"}),
            "dedup": f"{case_id}:{step}",
        },
    )


def intake(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    description = str(body.get("description") or "").strip()
    place = str(body.get("place_label") or "").strip()
    if not description or not place:
        raise CommandError(400, "invalid", "A report needs the affected place and a description.", False)
    source = str(body.get("source") or "resident")
    if source not in {"resident", "phone", "text", "email", "in_person", "worker"}:
        raise CommandError(400, "invalid", "That report source is not available.", False)
    place_kind = str(body.get("place_kind") or "unit")
    if place_kind not in {"unit", "building", "common_area", "vacant_home"}:
        raise CommandError(400, "invalid", "That place is not available.", False)
    urgency = body.get("urgency") if isinstance(body.get("urgency"), dict) else {}
    severity, safety = _severity(urgency)
    reported_at = datetime.now(timezone.utc)
    if body.get("reported_at"):
        reported_at = datetime.fromisoformat(str(body["reported_at"]))
        if reported_at.tzinfo is None:
            reported_at = reported_at.replace(tzinfo=timezone.utc)
    key = str(body.get("idempotency_key") or "")
    fingerprint = _fingerprint([source, place, description, json.dumps(urgency, sort_keys=True)])
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.report")
        replay = _replay(connection, key, fingerprint)
        if replay:
            replay["safety_message"] = safety
            replay["posted"] = False
            return replay
        before = _journals(connection)
        role = _role(connection)
        supplied_resident = body.get("resident_actor")
        if role in {"resident", "household_adult"}:
            if supplied_resident and str(supplied_resident) != str(actor):
                raise CommandError(403, "denied", "A household cannot attach a report to someone else.", False)
            source = "resident"
            resident_actor = actor
        elif supplied_resident:
            _require(connection, "maintenance.coordinate")
            visible = connection.execute(
                text(
                    "SELECT count(*) FROM memberships WHERE account_id = :account "
                    "AND role_name IN ('resident', 'household_adult') "
                    "AND organization_id = perchpoint.current_org() "
                    "AND (ended_at IS NULL OR ended_at > now())"
                ),
                {"account": supplied_resident},
            ).scalar_one()
            if not int(visible):
                raise CommandError(403, "denied", "That household is not available for this report.", False)
            resident_actor = supplied_resident
        else:
            resident_actor = None
        case_id = uuid4()
        reference = _reference("M")
        coordinator = _account_for_role(connection, "operations_manager")
        connection.execute(
            text("INSERT INTO maintenance_cases (organization_id, id, created_by) VALUES (:org, :id, perchpoint.current_actor())"),
            {"org": organization, "id": case_id},
        )
        connection.execute(
            text(
                "INSERT INTO maintenance_case_events (organization_id, id, case_id, event_type, content, actor_id) "
                "VALUES (:org, :id, :case, 'reported_problem', :content, perchpoint.current_actor())"
            ),
            {"org": organization, "id": uuid4(), "case": case_id, "content": description},
        )
        resident_actor = actor if source == "resident" else body.get("resident_actor")
        connection.execute(
            text(
                "INSERT INTO maintenance_reports (organization_id, id, case_id, public_reference, reporter_actor, resident_actor, entered_by, source, reported_at, place_kind, place_label, household_label, description, urgency, human_emergency, severity, safety_message, summary, coordinator_actor, ack_due_at, environment, money_moved, real_values_activated) "
                "VALUES (:org, :id, :case, :reference, perchpoint.current_actor(), :resident, perchpoint.current_actor(), :source, :reported, :place_kind, :place, :household, :description, CAST(:urgency AS jsonb), :emergency, :severity, :safety, 'received', :coordinator, :due, 'local_fake', false, false)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": case_id,
                "reference": reference,
                "resident": resident_actor,
                "source": source,
                "reported": reported_at,
                "place_kind": place_kind,
                "place": place,
                "household": body.get("household_label"),
                "description": description,
                "urgency": json.dumps(urgency),
                "emergency": bool(urgency.get("human_emergency") or urgency.get("immediate_danger")),
                "severity": severity,
                "safety": safety,
                "coordinator": coordinator,
                "due": _due(severity, reported_at),
            },
        )
        if body.get("access_instructions"):
            _require(connection, "maintenance.coordinate")
        if _journals(connection) != before:
            raise CommandError(409, "financial_effect", "Maintenance intake cannot change a financial journal.", False)
        _queue_escalation(connection, organization, case_id, severity, reported_at, bool(body.get("synthetic_fail_first_delivery")))
        _remember(connection, organization, key, fingerprint, reference)
    return {
        "accepted": True,
        "reference": reference,
        "severity": severity,
        "safety_message": safety,
        "summary": "received",
        "replayed": False,
        "money_moved": False,
        "real_values_activated": False,
    }


def record_access(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body.get("reference")))
        connection.execute(
            text("INSERT INTO maintenance_access (organization_id, id, case_id, instructions) VALUES (:org, :id, :case, :instructions)"),
            {"org": organization, "id": uuid4(), "case": report["case_id"], "instructions": str(body.get("instructions") or "")},
        )
    return {"accepted": True, "reference": body.get("reference")}


def mine(settings: Settings, actor, organization) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.report")
        rows = connection.execute(
            text(
                "SELECT public_reference, place_label, summary, severity, description, safety_message "
                "FROM maintenance_reports ORDER BY reported_at DESC"
            )
        ).mappings().all()
    return {"items": [dict(row) for row in rows], "money_moved": False}


def jobs(settings: Settings, actor, organization) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        rows = connection.execute(
            text(
                "SELECT report.public_reference, report.place_label, report.summary, report.severity, assignment.state "
                "FROM maintenance_assignments assignment "
                "JOIN maintenance_reports report ON report.case_id = assignment.case_id "
                "WHERE assignment.assignee_actor = perchpoint.current_actor() "
                "ORDER BY assignment.created_at DESC"
            )
        ).mappings().all()
    return {"items": [dict(row) for row in rows], "money_moved": False}


def queue(settings: Settings, actor, organization) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        rows = connection.execute(
            text(
                "SELECT public_reference, place_label, summary, severity, version, coordinator_actor IS NOT NULL AS owned, "
                "ack_due_at, human_emergency FROM maintenance_reports ORDER BY reported_at"
            )
        ).mappings().all()
        mismatches = connection.execute(
            text("SELECT count(*) FROM maintenance_compatibility WHERE result = 'rejected'")
        ).scalar_one()
    items = [dict(row) for row in rows]
    return {"items": items, "count": len(items), "material_mismatches": int(mismatches), "money_moved": False}


def detail(settings: Settings, actor, organization, reference: str) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        report = _report(connection, reference)
        role = _role(connection)
        needs = connection.execute(
            text("SELECT revision, specification, quantity, unit_name, model_number, dimensions, unknowns FROM maintenance_needs WHERE case_id = :case ORDER BY revision"),
            {"case": report["case_id"]},
        ).mappings().all()
        decisions = connection.execute(
            text("SELECT needs_revision, selected_specification, reason, amount_minor, authority, provisional FROM maintenance_decisions WHERE case_id = :case ORDER BY created_at"),
            {"case": report["case_id"]},
        ).mappings().all()
        received = connection.execute(
            text("SELECT COALESCE(sum(quantity_received), 0), COALESCE(sum(quantity_remaining), 0), COALESCE(sum(quantity_used), 0), COALESCE(sum(quantity_returned), 0) FROM maintenance_fulfillment WHERE case_id = :case"),
            {"case": report["case_id"]},
        ).one()
        notes = connection.execute(
            text("SELECT visibility, body, worsening FROM maintenance_notes WHERE case_id = :case ORDER BY created_at"),
            {"case": report["case_id"]},
        ).mappings().all()
        access = None
        if role in {"operations_manager", "owner", "maintenance", "maintenance_coordinator", "technician", "cleaner"}:
            access = connection.execute(
                text("SELECT instructions FROM maintenance_access WHERE case_id = :case"),
                {"case": report["case_id"]},
            ).scalar()
        notice = connection.execute(
            text("SELECT program, source_label, deadline_at, deadline_version FROM maintenance_notices WHERE case_id = :case"),
            {"case": report["case_id"]},
        ).mappings().first()
        planned = connection.execute(
            text("SELECT count(*) FROM maintenance_visits WHERE case_id = :case AND state = 'planned'"),
            {"case": report["case_id"]},
        ).scalar_one()
    resident_view = role in {"resident", "household_adult"}
    return {
        "reference": report["public_reference"],
        "version": report["version"],
        "summary": report["summary"],
        "severity": report["severity"],
        "place_label": report["place_label"],
        "description": report["description"],
        "reported_at": report["reported_at"].isoformat(),
        "safety_message": report["safety_message"],
        "needs": [dict(row) for row in needs] if not resident_view else [],
        "decisions": [dict(row) for row in decisions] if not resident_view else [],
        "received_quantity": float(received[0]) if not resident_view else None,
        "remaining_quantity": float(received[1]) if not resident_view else None,
        "used_quantity": float(received[2]) if not resident_view else None,
        "returned_quantity": float(received[3]) if not resident_view else None,
        "ready": False if not resident_view and (not decisions or float(received[1]) > 0) else None,
        "notes": [dict(row) for row in notes if not resident_view or row["visibility"] == "resident"],
        "access_instructions": None if resident_view else access,
        "notice": dict(notice) if notice and not resident_view else None,
        "on_the_way": report["summary"] == "visit_planned" and int(planned) > 0,
        "money_moved": False,
        "real_values_activated": False,
    }


def acknowledge(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body["reference"]))
        updated = connection.execute(
            text(
                "UPDATE maintenance_reports SET summary = 'reviewed', version = version + 1 "
                "WHERE public_reference = :reference AND version = :version RETURNING version"
            ),
            {"reference": body["reference"], "version": body["version"]},
        ).scalar()
        if updated is None:
            raise CommandError(409, "conflict", "That case changed. Reload it and try again.", False)
        connection.execute(
            text("UPDATE maintenance_escalations SET state = 'acknowledged', human_acknowledged = true WHERE case_id = :case AND state = 'queued'"),
            {"case": report["case_id"]},
        )
    return {"accepted": True, "human_acknowledged": True, "delivery_is_acceptance": False, "version": updated}


def propose_assignment(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body["reference"]))
        assignee = body.get("assignee_actor") or _account_for_role(connection, "technician")
        connection.execute(
            text(
                "INSERT INTO maintenance_assignments (organization_id, id, case_id, assignee_actor, state, reason) "
                "VALUES (:org, :id, :case, :assignee, 'proposed', :reason)"
            ),
            {"org": organization, "id": uuid4(), "case": report["case_id"], "assignee": assignee, "reason": body.get("reason")},
        )
    return {"accepted": True, "state": "proposed", "coordinator_continues": True}


def respond_assignment(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    state = str(body.get("state") or "")
    if state not in {"accepted", "declined"}:
        raise CommandError(400, "invalid", "Accept the assignment or decline it with a reason.", False)
    if state == "declined" and not str(body.get("reason") or "").strip():
        raise CommandError(400, "invalid", "A decline needs a reason.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        report = _report(connection, str(body["reference"]))
        updated = connection.execute(
            text(
                "UPDATE maintenance_assignments SET state = :state, reason = :reason, version = version + 1 "
                "WHERE case_id = :case AND assignee_actor = perchpoint.current_actor() AND state = 'proposed' RETURNING id"
            ),
            {"state": state, "reason": body.get("reason"), "case": report["case_id"]},
        ).scalar()
        if updated is None:
            raise CommandError(409, "conflict", "That assignment is no longer waiting for you.", False)
        if state == "accepted":
            connection.execute(
                text("UPDATE maintenance_reports SET summary = 'accepted', version = version + 1 WHERE case_id = :case"),
                {"case": report["case_id"]},
            )
    return {"accepted": True, "state": state}


def add_need(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    specification = str(body.get("specification") or "").strip()
    if not specification:
        raise CommandError(400, "invalid", "Describe the needed part or say that no material is required.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        report = _report(connection, str(body["reference"]))
        revision = int(connection.execute(
            text("SELECT COALESCE(max(revision), 0) + 1 FROM maintenance_needs WHERE case_id = :case"),
            {"case": report["case_id"]},
        ).scalar_one())
        connection.execute(
            text(
                "INSERT INTO maintenance_needs (organization_id, id, case_id, revision, author_actor, specification, quantity, unit_name, manufacturer, model_number, dimensions, alternatives, unknowns) "
                "VALUES (:org, :id, :case, :revision, perchpoint.current_actor(), :specification, :quantity, :unit, :manufacturer, :model, :dimensions, :alternatives, :unknowns)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "revision": revision,
                "specification": specification,
                "quantity": body.get("quantity") or 1,
                "unit": body.get("unit_name") or "each",
                "manufacturer": body.get("manufacturer"),
                "model": body.get("model_number"),
                "dimensions": body.get("dimensions"),
                "alternatives": body.get("alternatives"),
                "unknowns": body.get("unknowns"),
            },
        )
        connection.execute(
            text(
                "INSERT INTO maintenance_case_events (organization_id, id, case_id, event_type, content, actor_id) "
                "VALUES (:org, :id, :case, 'technician_recommendation', :content, perchpoint.current_actor())"
            ),
            {"org": organization, "id": uuid4(), "case": report["case_id"], "content": specification},
        )
    return {"accepted": True, "revision": revision}


def decide(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    amount = int(body.get("amount_minor") or 0)
    authority = str(body.get("authority") or "routine")
    if authority not in {"routine", "emergency_provisional", "owner"}:
        raise CommandError(400, "invalid", "That authority is not available.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "purchase.authorize")
        role = _role(connection)
        if role in {"technician", "cleaner", "vendor_worker"}:
            raise CommandError(403, "denied", "Workers have no standing purchasing authority.", False)
        report = _report(connection, str(body["reference"]))
        current = connection.execute(
            text("SELECT revision, specification FROM maintenance_needs WHERE case_id = :case ORDER BY revision DESC LIMIT 1"),
            {"case": report["case_id"]},
        ).mappings().first()
        if current is None:
            raise CommandError(400, "invalid", "There is no worker recommendation to decide.", False)
        if int(body.get("needs_revision") or current["revision"]) != int(current["revision"]):
            raise CommandError(409, "conflict", "A decision cannot approve an older recommendation.", False)
        spent = int(connection.execute(
            text("SELECT COALESCE(sum(amount_minor), 0) FROM maintenance_decisions WHERE case_id = :case"),
            {"case": report["case_id"]},
        ).scalar_one())
        total = spent + amount
        if role != "owner":
            if authority == "owner" or total > EMERGENCY_LIMIT:
                raise CommandError(403, "denied", "That exposure is reserved for the owner.", False)
            if authority == "routine" and total > ROUTINE_LIMIT:
                raise CommandError(403, "denied", "Routine authority stops at $1,200. Related items cannot be split.", False)
            if authority == "emergency_provisional" and total > EMERGENCY_LIMIT:
                raise CommandError(403, "denied", "The provisional emergency allowance is $2,500.", False)
        before = _journals(connection)
        provisional = authority == "emergency_provisional"
        connection.execute(
            text(
                "INSERT INTO maintenance_decisions (organization_id, id, case_id, needs_revision, actor_id, selected_specification, reason, amount_minor, authority, provisional) "
                "VALUES (:org, :id, :case, :revision, perchpoint.current_actor(), :selected, :reason, :amount, :authority, :provisional)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "revision": current["revision"],
                "selected": str(body.get("selected_specification") or current["specification"]),
                "reason": str(body.get("reason") or ""),
                "amount": amount,
                "authority": authority,
                "provisional": provisional,
            },
        )
        connection.execute(
            text(
                "INSERT INTO maintenance_case_events (organization_id, id, case_id, event_type, content, actor_id) "
                "VALUES (:org, :id, :case, 'manager_decision', :content, perchpoint.current_actor())"
            ),
            {"org": organization, "id": uuid4(), "case": report["case_id"], "content": str(body.get("reason") or "")},
        )
        if _journals(connection) != before:
            raise CommandError(409, "financial_effect", "A maintenance decision cannot post a journal.", False)
    return {
        "accepted": True,
        "needs_revision": int(current["revision"]),
        "original_specification": current["specification"],
        "provisional": authority == "emergency_provisional",
        "money_moved": False,
        "real_values_activated": False,
    }


def record_fulfillment(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    received = float(body.get("quantity_received") or 0)
    remaining = float(body.get("quantity_remaining") or 0)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body["reference"]))
        decision = connection.execute(
            text("SELECT id FROM maintenance_decisions WHERE case_id = :case ORDER BY created_at DESC LIMIT 1"),
            {"case": report["case_id"]},
        ).scalar()
        if decision is None:
            raise CommandError(400, "invalid", "Record a decision before recording what arrived.", False)
        connection.execute(
            text(
                "INSERT INTO maintenance_fulfillment (organization_id, id, case_id, decision_id, quantity_received, quantity_remaining, quantity_used, quantity_returned, condition, reference_label, actor_id) "
                "VALUES (:org, :id, :case, :decision, :received, :remaining, :used, :returned, :condition, :label, perchpoint.current_actor())"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "decision": decision,
                "received": received,
                "remaining": remaining,
                "used": body.get("quantity_used") or 0,
                "returned": body.get("quantity_returned") or 0,
                "condition": str(body.get("condition") or "received"),
                "label": body.get("reference_label"),
            },
        )
    return {"accepted": True, "ready": remaining == 0 and received > 0, "money_moved": False}


def check_compatibility(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    result = str(body.get("result") or "")
    if result not in {"accepted", "partial", "rejected"}:
        raise CommandError(400, "invalid", "Accept, partially accept, or reject the materials.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        report = _report(connection, str(body["reference"]))
        revision = int(connection.execute(
            text("SELECT COALESCE(max(revision), 0) FROM maintenance_needs WHERE case_id = :case"),
            {"case": report["case_id"]},
        ).scalar_one())
        if int(body.get("needs_revision") or 0) != revision:
            raise CommandError(409, "conflict", "An older acknowledgment cannot cover the current materials.", False)
        connection.execute(
            text(
                "INSERT INTO maintenance_compatibility (organization_id, id, case_id, needs_revision, result, mismatch, actor_id) "
                "VALUES (:org, :id, :case, :revision, :result, :mismatch, perchpoint.current_actor())"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "revision": revision,
                "result": result,
                "mismatch": body.get("mismatch"),
            },
        )
        if result == "rejected":
            resolver = report["coordinator_actor"] or _account_for_role(connection, "operations_manager")
            if resolver is None:
                raise CommandError(409, "conflict", "No coordinator is available to own this blocker.", False)
            connection.execute(
                text(
                    "INSERT INTO maintenance_blockers (organization_id, id, case_id, kind, resolver_actor, reason, next_update_at, state) "
                    "VALUES (:org, :id, :case, 'incorrect_materials', :resolver, :reason, now() + interval '1 day', 'open')"
                ),
                {"org": organization, "id": uuid4(), "case": report["case_id"], "resolver": resolver, "reason": body.get("mismatch") or "The delivered material does not match the approved specification."},
            )
    return {"accepted": True, "ready": result == "accepted", "result": result}


def start_time(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    key = str(body.get("idempotency_key") or "")
    fingerprint = _fingerprint(["start", body.get("reference"), body.get("category")])
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        replay = _replay(connection, key, fingerprint)
        if replay:
            return replay
        report = _report(connection, str(body["reference"]))
        interval_id = uuid4()
        reference = _reference("T")
        try:
            connection.execute(
                text(
                    "INSERT INTO maintenance_time_intervals (organization_id, id, case_id, actor_id, category, started_at, source, description) "
                    "VALUES (:org, :id, :case, perchpoint.current_actor(), :category, now(), 'timer', :description)"
                ),
                {"org": organization, "id": interval_id, "case": report["case_id"], "category": body.get("category") or "on_site", "description": body.get("description")},
            )
        except IntegrityError as exc:
            raise CommandError(409, "conflict", "You already have an open time interval.", False) from exc
        _remember(connection, organization, key, fingerprint, reference)
    return {"accepted": True, "reference": reference, "saved": True, "replayed": False}


def stop_time(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    key = str(body.get("idempotency_key") or "")
    fingerprint = _fingerprint(["stop", body.get("reference")])
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        replay = _replay(connection, key, fingerprint)
        if replay:
            return replay
        updated = connection.execute(
            text(
                "UPDATE maintenance_time_intervals SET ended_at = COALESCE(CAST(:reported AS timestamptz), now()), server_ended_at = now(), version = version + 1 "
                "WHERE actor_id = perchpoint.current_actor() AND ended_at IS NULL RETURNING id"
            ),
            {"reported": body.get("reported_event_at")},
        ).scalar()
        if updated is None:
            raise CommandError(409, "conflict", "There is no open interval to stop.", False)
        reference = _reference("T")
        _remember(connection, organization, key, fingerprint, reference)
    return {"accepted": True, "reference": reference, "saved": True, "requires_photos": False, "requires_location": False}


def add_manual_time(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    if not str(body.get("reason") or "").strip():
        raise CommandError(400, "invalid", "A manual time entry needs a reason.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        report = _report(connection, str(body["reference"]))
        started = datetime.fromisoformat(str(body["started_at"]))
        ended = datetime.fromisoformat(str(body["ended_at"]))
        overlap = connection.execute(
            text(
                "SELECT count(*) FROM maintenance_time_intervals WHERE actor_id = perchpoint.current_actor() "
                "AND started_at < :ended AND COALESCE(ended_at, now()) > :started"
            ),
            {"started": started, "ended": ended},
        ).scalar_one()
        connection.execute(
            text(
                "INSERT INTO maintenance_time_intervals (organization_id, id, case_id, actor_id, category, started_at, ended_at, server_ended_at, source, description, overlap_flag) "
                "VALUES (:org, :id, :case, perchpoint.current_actor(), :category, :started, :ended, now(), 'manual', :reason, :overlap)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "category": body.get("category") or "waiting",
                "started": started,
                "ended": ended,
                "reason": body["reason"],
                "overlap": int(overlap) > 0,
            },
        )
    return {"accepted": True, "overlap_flag": int(overlap) > 0, "saved": True}


def correct_time(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        role = _role(connection)
        if role in {"technician", "cleaner"}:
            _require(connection, "work.assign")
            state = "proposed"
            reviewer = None
        else:
            _require(connection, "maintenance.coordinate")
            if str(body.get("interval_actor") or "") == str(actor):
                raise CommandError(403, "denied", "You cannot approve your own time correction.", False)
            state = "approved"
            reviewer = actor
        connection.execute(
            text(
                "INSERT INTO maintenance_time_adjustments (organization_id, id, interval_id, actor_id, reason, reviewer_actor, state) "
                "VALUES (:org, :id, :interval, perchpoint.current_actor(), :reason, :reviewer, :state)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "interval": body["interval_id"],
                "reason": body.get("reason"),
                "reviewer": reviewer,
                "state": state,
            },
        )
    return {"accepted": True, "state": state}


def check_in(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    outcome = str(body.get("outcome") or "unavailable")
    if outcome not in {"synthetic", "denied", "timeout", "inaccurate", "unavailable", "unsupported"}:
        raise CommandError(400, "invalid", "That location outcome is not available.", False)
    if outcome == "synthetic" and os.environ.get("PHASE3_ENVIRONMENT", "local") not in {"local", "test"}:
        raise CommandError(403, "denied", "Real location collection is not active.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        report = _report(connection, str(body["reference"]))
        latitude = body.get("latitude") if outcome == "synthetic" else None
        longitude = body.get("longitude") if outcome == "synthetic" else None
        connection.execute(
            text(
                "INSERT INTO maintenance_locations (organization_id, id, case_id, actor_id, latitude, longitude, accuracy_meters, outcome, observed_at) "
                "VALUES (:org, :id, :case, perchpoint.current_actor(), :latitude, :longitude, :accuracy, :outcome, now())"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "latitude": latitude,
                "longitude": longitude,
                "accuracy": body.get("accuracy_meters"),
                "outcome": outcome,
            },
        )
        connection.execute(
            text(
                "INSERT INTO maintenance_location_audit (organization_id, id, case_id, actor_id, outcome, observed_at) "
                "VALUES (:org, :id, :case, perchpoint.current_actor(), :outcome, now())"
            ),
            {"org": organization, "id": uuid4(), "case": report["case_id"], "outcome": outcome},
        )
    return {"accepted": True, "outcome": outcome, "proves_presence": False, "saved": True}


def read_locations(settings: Settings, actor, organization, reference: str) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        report = _report(connection, reference)
        rows = connection.execute(
            text("SELECT outcome, latitude, longitude FROM maintenance_locations WHERE case_id = :case AND deleted_at IS NULL"),
            {"case": report["case_id"]},
        ).mappings().all()
    return {"items": [dict(row) for row in rows]}


def _scan(content: bytes) -> str:
    if len(content) > MAX_UPLOAD:
        raise CommandError(413, "invalid", "That file is too large.", False)
    if content.startswith(b"\xff\xd8\xff") or content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "available"
    if content.startswith(b"<") or b"<script" in content.lower():
        raise CommandError(400, "invalid", "That file is not an accepted photo.", False)
    raise CommandError(400, "invalid", "Use a JPEG or PNG photo.", False)


def add_evidence(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    content = bytes.fromhex(str(body.get("content_hex") or ""))
    scan_state = _scan(content)
    digest = hashlib.sha256(content).hexdigest()
    stage = str(body.get("stage") or "")
    if stage not in {"before", "after", "arrival", "departure"}:
        raise CommandError(400, "invalid", "Label the photo before, after, arrival, or departure.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        report = _report(connection, str(body["reference"]))
        visit = connection.execute(
            text("SELECT id FROM maintenance_visits WHERE case_id = :case ORDER BY created_at DESC LIMIT 1"),
            {"case": report["case_id"]},
        ).scalar()
        if visit is None:
            visit = uuid4()
            connection.execute(
                text("INSERT INTO maintenance_visits (organization_id, id, case_id, actor_id, state) VALUES (:org, :id, :case, perchpoint.current_actor(), 'planned')"),
                {"org": organization, "id": visit, "case": report["case_id"]},
            )
        opposite = "before" if stage == "after" else "after" if stage == "before" else None
        if opposite:
            reused = connection.execute(
                text("SELECT count(*) FROM maintenance_evidence WHERE case_id = :case AND content_sha = :sha AND stage = :stage"),
                {"case": report["case_id"], "sha": digest, "stage": opposite},
            ).scalar_one()
            if int(reused):
                raise CommandError(409, "conflict", "A before photo cannot silently satisfy the after photo.", False)
        connection.execute(
            text(
                "INSERT INTO maintenance_evidence (organization_id, id, case_id, visit_id, stage, caption, content_sha, scan_state, uploader_actor, captured_at) "
                "VALUES (:org, :id, :case, :visit, :stage, :caption, :sha, :scan, perchpoint.current_actor(), :captured)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "visit": visit,
                "stage": stage,
                "caption": str(body.get("caption") or ""),
                "sha": digest,
                "scan": scan_state,
                "captured": body.get("captured_at"),
            },
        )
    return {"accepted": True, "scan_state": scan_state, "clean": scan_state == "available", "saved": True}


def submit_completion(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "work.assign")
        report = _report(connection, str(body["reference"]))
        stages = {row[0] for row in connection.execute(
            text("SELECT stage FROM maintenance_evidence WHERE case_id = :case AND scan_state = 'available'"),
            {"case": report["case_id"]},
        )}
        exception = str(body.get("exception_reason") or "")
        inspection = bool(body.get("inspection_only"))
        required = {"arrival", "departure"} if inspection else {"before", "after"}
        if not required.issubset(stages):
            if exception not in {"safety", "no_access", "privacy", "upload_failure"}:
                raise CommandError(409, "evidence_missing", "Completion needs the required before and after evidence.", False)
        visit = uuid4()
        connection.execute(
            text("UPDATE maintenance_visits SET state = 'submitted' WHERE case_id = :case AND state = 'planned'"),
            {"case": report["case_id"]},
        )
        connection.execute(
            text(
                "INSERT INTO maintenance_visits (organization_id, id, case_id, actor_id, state, exception_reason) "
                "VALUES (:org, :id, :case, perchpoint.current_actor(), 'submitted', :exception)"
            ),
            {"org": organization, "id": visit, "case": report["case_id"], "exception": exception or None},
        )
        connection.execute(
            text(
                "UPDATE maintenance_reports SET summary = 'accepted', version = version + 1 "
                "WHERE case_id = :case AND summary = 'visit_planned'"
            ),
            {"case": report["case_id"]},
        )
    return {"accepted": True, "verified": False, "exception": bool(exception), "visit_id": str(visit), "on_the_way": False}


def review_completion(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    outcome = str(body.get("outcome") or "")
    if outcome not in {"verified", "clarification", "reopened"}:
        raise CommandError(400, "invalid", "Verify the work, request clarification, or reopen it.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body["reference"]))
        visit = connection.execute(
            text("SELECT id, actor_id FROM maintenance_visits WHERE case_id = :case AND state = 'submitted' ORDER BY created_at DESC LIMIT 1"),
            {"case": report["case_id"]},
        ).mappings().first()
        if visit is None:
            raise CommandError(404, "missing", "There is no submitted visit to review.", False)
        if visit["actor_id"] == _org(actor):
            raise CommandError(403, "denied", "The person who submitted the work cannot verify it.", False)
        connection.execute(
            text(
                "INSERT INTO maintenance_reviews (organization_id, id, visit_id, submitter_actor, reviewer_actor, outcome, reason) "
                "VALUES (:org, :id, :visit, :submitter, perchpoint.current_actor(), :outcome, :reason)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "visit": visit["id"],
                "submitter": visit["actor_id"],
                "outcome": outcome,
                "reason": str(body.get("reason") or ""),
            },
        )
        summary = "completed" if outcome == "verified" else "accepted"
        connection.execute(
            text("UPDATE maintenance_visits SET state = :state WHERE id = :id"),
            {"state": outcome if outcome != "verified" else "verified", "id": visit["id"]},
        )
        connection.execute(
            text("UPDATE maintenance_reports SET summary = :summary, version = version + 1 WHERE case_id = :case"),
            {"summary": summary, "case": report["case_id"]},
        )
    return {"accepted": True, "outcome": outcome, "resident_silence_is_confirmation": False}


def plan_visit(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body["reference"]))
        connection.execute(
            text(
                "INSERT INTO maintenance_visits (organization_id, id, case_id, actor_id, state) "
                "VALUES (:org, :id, :case, perchpoint.current_actor(), 'planned')"
            ),
            {"org": organization, "id": uuid4(), "case": report["case_id"]},
        )
        connection.execute(
            text("UPDATE maintenance_reports SET summary = 'visit_planned', version = version + 1 WHERE case_id = :case"),
            {"case": report["case_id"]},
        )
    return {"accepted": True, "summary": "visit_planned", "on_the_way": True}


def withdraw(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    reason = str(body.get("reason") or "").strip()
    if not reason:
        raise CommandError(400, "invalid", "Withdrawal needs a reason.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        report = _report(connection, str(body["reference"]))
        role = _role(connection)
        if role not in {"operations_manager", "owner", "maintenance", "maintenance_coordinator"} and report["reporter_actor"] != _org(actor):
            raise CommandError(403, "denied", "Only the reporter or a coordinator can withdraw this request.", False)
        connection.execute(
            text("UPDATE maintenance_reports SET summary = 'withdrawn', version = version + 1 WHERE case_id = :case"),
            {"case": report["case_id"]},
        )
    return {"accepted": True, "summary": "withdrawn", "evidence_retained": True}


def add_notice(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body["reference"]))
        before = _journals(connection)
        deadline = datetime.fromisoformat(str(body["deadline_at"]))
        connection.execute(
            text(
                "INSERT INTO maintenance_notices (organization_id, id, case_id, program, source_label, deficiency, deadline_at, deadline_version, owner_actor) "
                "VALUES (:org, :id, :case, :program, :source, :deficiency, :deadline, :version, perchpoint.current_actor())"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "program": body.get("program"),
                "source": body.get("source_label"),
                "deficiency": body.get("deficiency"),
                "deadline": deadline,
                "version": int(body.get("deadline_version") or 1),
            },
        )
        if _journals(connection) != before:
            raise CommandError(409, "financial_effect", "An inspection notice cannot change a balance.", False)
        stored = connection.execute(
            text("SELECT deadline_at FROM maintenance_notices WHERE case_id = :case"),
            {"case": report["case_id"]},
        ).scalar_one()
    return {"accepted": True, "deadline_at": stored.isoformat(), "money_moved": False}


def add_note(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    visibility = str(body.get("visibility") or "internal")
    if visibility not in {"resident", "internal"}:
        raise CommandError(400, "invalid", "Choose resident-visible or internal.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        report = _report(connection, str(body["reference"]))
        if _role(connection) in {"resident", "household_adult"}:
            visibility = "resident"
        connection.execute(
            text(
                "INSERT INTO maintenance_notes (organization_id, id, case_id, actor_id, visibility, body, worsening) "
                "VALUES (:org, :id, :case, perchpoint.current_actor(), :visibility, :body, :worsening)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "case": report["case_id"],
                "visibility": visibility,
                "body": str(body.get("body") or ""),
                "worsening": bool(body.get("worsening")),
            },
        )
        if body.get("worsening"):
            _queue_escalation(connection, organization, report["case_id"], "emergency", datetime.now(timezone.utc), False)
    return {"accepted": True}


def link_cases(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body["reference"]))
        other = _report(connection, str(body["other_reference"]))
        original = report["reported_at"]
        connection.execute(
            text("UPDATE maintenance_reports SET linked_case_id = :other, version = version + 1 WHERE case_id = :case"),
            {"other": other["case_id"], "case": report["case_id"]},
        )
        kept = connection.execute(
            text("SELECT reported_at FROM maintenance_reports WHERE case_id = :case"),
            {"case": report["case_id"]},
        ).scalar_one()
    return {"accepted": True, "reported_at": kept.isoformat(), "original_preserved": kept == original}


def change_severity(settings: Settings, actor, organization, body: dict) -> dict:
    organization = _org(organization)
    severity = str(body.get("severity") or "")
    if severity not in {"emergency", "urgent", "routine"} or not str(body.get("reason") or "").strip():
        raise CommandError(400, "invalid", "A severity change needs a reason and a known severity.", False)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        report = _report(connection, str(body["reference"]))
        if report["human_emergency"] and severity != "emergency" and not body.get("supervisory"):
            raise CommandError(403, "denied", "A human emergency flag cannot be quietly downgraded.", False)
        connection.execute(
            text("UPDATE maintenance_reports SET severity = :severity, version = version + 1 WHERE public_reference = :reference"),
            {"severity": severity, "reference": body["reference"]},
        )
    return {"accepted": True, "previous": report["severity"], "severity": severity, "reported_at": report["reported_at"].isoformat()}


def briefing(settings: Settings, actor, organization) -> dict:
    organization = _org(organization)
    with runtime_transaction(settings, _org(actor), organization, uuid4()) as connection:
        _require(connection, "maintenance.coordinate")
        rows = connection.execute(
            text(
                "SELECT public_reference, place_label, severity, summary, ack_due_at < now() AS overdue "
                "FROM maintenance_reports WHERE severity = 'emergency' OR summary IN ('received', 'accepted') "
                "ORDER BY reported_at LIMIT 8"
            )
        ).mappings().all()
        blocked = connection.execute(
            text(
                "SELECT report.public_reference, blocker.kind, blocker.reason FROM maintenance_blockers blocker "
                "JOIN maintenance_reports report ON report.case_id = blocker.case_id WHERE blocker.state = 'open'"
            )
        ).mappings().all()
        count = connection.execute(text("SELECT count(*) FROM maintenance_reports")).scalar_one()
    return {
        "decisions_needed": [dict(row) for row in rows],
        "blocked": [dict(row) for row in blocked],
        "queue_count": int(count),
        "money_moved": False,
        "real_values_activated": False,
    }


def process_escalations(settings: Settings) -> dict:
    from .phase6_identity import authenticate_service_credential

    principal = authenticate_service_credential(
        settings,
        os.environ.get("PHASE6_WORKER_CREDENTIAL", "local-only-not-production-worker-credential"),
        audience="perchpoint-worker",
        worker_name=os.environ.get("PHASE6_WORKER_NAME", "synthetic-worker"),
    )
    if principal is None:
        raise CommandError(401, "service_credential_invalid", "Worker authentication failed.", False)
    applied = 0
    with runtime_transaction(settings, principal["id"], principal["organization_id"], uuid4()) as connection:
        if os.environ.get("PHASE3_ENVIRONMENT", "local") in {"local", "test"} and os.environ.get("PHASE20_FAULT") == "before_commit":
            raise RuntimeError("injected fault")
        row = connection.execute(
            text(
                "SELECT id, case_id, step, recipient_role, fail_delivery, human_acknowledged FROM maintenance_escalations "
                "WHERE state = 'queued' ORDER BY created_at FOR UPDATE SKIP LOCKED LIMIT 1"
            )
        ).mappings().first()
        if row is None:
            return {"applied": 0, "claimed": False}
        if row["human_acknowledged"]:
            connection.execute(
                text("UPDATE maintenance_escalations SET state = 'acknowledged' WHERE id = :id"),
                {"id": row["id"]},
            )
            return {"applied": 0, "claimed": True, "state": "acknowledged"}
        if row["fail_delivery"]:
            connection.execute(
                text("UPDATE maintenance_escalations SET state = 'failed' WHERE id = :id"),
                {"id": row["id"]},
            )
            next_step = int(row["step"]) + 1
            role = "owner" if next_step >= 1 else "technician"
            dedup = f"{row['case_id']}:{next_step}"
            exists = connection.execute(
                text("SELECT count(*) FROM maintenance_escalations WHERE dedup_key = :dedup"),
                {"dedup": dedup},
            ).scalar_one()
            if int(exists) == 0 and next_step <= 2:
                connection.execute(
                    text(
                        "INSERT INTO maintenance_escalations (organization_id, id, case_id, step, recipient_role, state, dedup_key) "
                        "VALUES (:org, :id, :case, :step, :role, 'queued', :dedup)"
                    ),
                    {"org": principal["organization_id"], "id": uuid4(), "case": row["case_id"], "step": next_step, "role": role, "dedup": dedup},
                )
            elif next_step > 2:
                connection.execute(
                    text(
                        "INSERT INTO maintenance_escalations (organization_id, id, case_id, step, recipient_role, state, dedup_key) "
                        "VALUES (:org, :id, :case, :step, 'owner', 'unresolved', :dedup)"
                    ),
                    {"org": principal["organization_id"], "id": uuid4(), "case": row["case_id"], "step": next_step, "dedup": dedup},
                )
            applied = 1
            state = "failed"
        else:
            connection.execute(
                text("UPDATE maintenance_escalations SET state = 'delivered', human_acknowledged = false WHERE id = :id"),
                {"id": row["id"]},
            )
            applied = 1
            state = "delivered"
    return {"applied": applied, "claimed": True, "state": state, "human_acknowledged": False}


def seed_demo_stories(connection, organization, resident, coordinator, technician, owner) -> None:
    """Idempotent synthetic stories. They do not post journals or change October balances."""
    from foundation.seeds import sid

    if connection.execute(text("SELECT to_regclass('public.maintenance_reports')")).scalar() is None:
        return

    stories = [
        ("routine", "PP-M20-01", "resident", "unit", "Maple Court 101", "The kitchen faucet drips.", "routine", "received", False, "2026-10-10T14:00:00+00:00"),
        ("emergency", "PP-M20-02", "phone", "unit", "Sycamore House 2", "Water is coming through the ceiling.", "emergency", "received", True, "2026-10-11T02:00:00+00:00"),
        ("after-hours", "PP-M20-03", "text", "unit", "Brookside House 4", "The heat is out.", "urgent", "received", False, "2026-10-11T03:30:00+00:00"),
        ("wrong-part", "PP-M20-04", "worker", "unit", "Maple Court 102", "The cartridge does not match the faucet.", "routine", "accepted", False, "2026-10-09T15:00:00+00:00"),
        ("partial", "PP-M20-05", "email", "unit", "Maple Court 103", "Only one of two valves arrived.", "routine", "accepted", False, "2026-10-08T15:00:00+00:00"),
        ("repeat", "PP-M20-06", "resident", "unit", "Maple Court 101", "The faucet is dripping again.", "routine", "received", False, "2026-10-12T15:00:00+00:00"),
        ("common", "PP-M20-07", "in_person", "common_area", "Sycamore House hallway", "The hallway light is out.", "routine", "reviewed", False, "2026-10-07T15:00:00+00:00"),
        ("inspection", "PP-M20-08", "email", "unit", "Brookside House 1", "The notice cites a missing handrail.", "urgent", "reviewed", False, "2026-10-06T15:00:00+00:00"),
        ("access", "PP-M20-09", "phone", "vacant_home", "Elm Court vacant", "The lockbox code did not work.", "routine", "accepted", False, "2026-10-05T15:00:00+00:00"),
        ("complete", "PP-M20-10", "resident", "unit", "Maple Court 104", "The disposal was replaced.", "routine", "completed", False, "2026-10-04T15:00:00+00:00"),
    ]
    for key, reference, source, place_kind, place, description, severity, summary, emergency, reported in stories:
        case_id = sid(f"phase20-case-{key}")
        connection.execute(
            text(
                "INSERT INTO maintenance_cases (organization_id, id, status, created_by) "
                "VALUES (:org, :id, 'open', :actor) ON CONFLICT (organization_id, id) DO NOTHING"
            ),
            {"org": organization, "id": case_id, "actor": coordinator},
        )
        connection.execute(
            text(
                "INSERT INTO maintenance_case_events (organization_id, id, case_id, event_type, content, actor_id, occurred_at) "
                "VALUES (:org, :id, :case, 'reported_problem', :content, :actor, :occurred) ON CONFLICT (organization_id, id) DO NOTHING"
            ),
            {"org": organization, "id": sid(f"phase20-event-{key}"), "case": case_id, "content": description, "actor": resident, "occurred": reported},
        )
        connection.execute(
            text(
                "INSERT INTO maintenance_reports ("
                "organization_id, id, case_id, public_reference, reporter_actor, resident_actor, entered_by, source, "
                "reported_at, place_kind, place_label, description, urgency, human_emergency, severity, summary, "
                "coordinator_actor, ack_due_at, environment, money_moved, real_values_activated"
                ") VALUES ("
                ":org, :id, :case, :reference, :reporter, :resident, :entered, :source, :reported, :place_kind, :place, "
                ":description, CAST(:urgency AS jsonb), :emergency, :severity, :summary, :coordinator, :reported, "
                "'local_fake', false, false"
                ") ON CONFLICT (public_reference) DO NOTHING"
            ),
            {
                "org": organization,
                "id": sid(f"phase20-report-{key}"),
                "case": case_id,
                "reference": reference,
                "reporter": resident if source == "resident" else coordinator,
                "resident": resident,
                "entered": coordinator,
                "source": source,
                "reported": reported,
                "place_kind": place_kind,
                "place": place,
                "description": description,
                "urgency": json.dumps({"human_emergency": emergency}),
                "emergency": emergency,
                "severity": severity,
                "summary": summary,
                "coordinator": coordinator,
            },
        )
    connection.execute(
        text("UPDATE maintenance_reports SET linked_case_id = :original WHERE public_reference = 'PP-M20-06' AND linked_case_id IS NULL"),
        {"original": sid("phase20-case-routine")},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_assignments (organization_id, id, case_id, assignee_actor, state) "
            "VALUES (:org, :id, :case, :assignee, 'accepted') ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-assignment-wrong"), "case": sid("phase20-case-wrong-part"), "assignee": technician},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_needs (organization_id, id, case_id, revision, author_actor, specification, quantity, unit_name, model_number) "
            "VALUES (:org, :id, :case, 1, :author, 'Moen 7594 cartridge', 1, 'each', '7594') ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-need-wrong"), "case": sid("phase20-case-wrong-part"), "author": technician},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_decisions (organization_id, id, case_id, needs_revision, actor_id, selected_specification, reason, amount_minor, authority, provisional) "
            "VALUES (:org, :id, :case, 1, :actor, 'Generic cartridge', 'The specified part was unavailable.', 4000, 'routine', false) "
            "ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-decision-wrong"), "case": sid("phase20-case-wrong-part"), "actor": coordinator},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_compatibility (organization_id, id, case_id, needs_revision, actor_id, result, mismatch) "
            "VALUES (:org, :id, :case, 1, :actor, 'rejected', 'The delivered cartridge is the wrong diameter.') ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-compat-wrong"), "case": sid("phase20-case-wrong-part"), "actor": technician},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_blockers (organization_id, id, case_id, kind, resolver_actor, reason, next_update_at, state) "
            "VALUES (:org, :id, :case, 'incorrect_materials', :resolver, 'The wrong cartridge arrived.', '2026-10-13T15:00:00+00:00', 'open') "
            "ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-blocker-wrong"), "case": sid("phase20-case-wrong-part"), "resolver": coordinator},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_fulfillment (organization_id, id, case_id, decision_id, quantity_received, quantity_remaining, condition, reference_label, actor_id) "
            "VALUES (:org, :id, :case, :decision, 1, 1, 'partial', 'One valve of two', :actor) ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-fulfill-partial"), "case": sid("phase20-case-partial"), "decision": sid("phase20-decision-partial"), "actor": coordinator},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_decisions (organization_id, id, case_id, needs_revision, actor_id, selected_specification, reason, amount_minor, authority, provisional) "
            "VALUES (:org, :id, :case, 1, :actor, 'Shutoff valve', 'Two valves were approved.', 6000, 'routine', false) ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-decision-partial"), "case": sid("phase20-case-partial"), "actor": coordinator},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_notices (organization_id, id, case_id, program, source_label, deficiency, deadline_at, deadline_version, owner_actor) "
            "VALUES (:org, :id, :case, 'HCV', 'Synthetic notice 2026-10', 'Missing handrail', '2026-10-28T16:00:00+00:00', 2, :owner) "
            "ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-notice"), "case": sid("phase20-case-inspection"), "owner": owner},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_access (organization_id, id, case_id, instructions) "
            "VALUES (:org, :id, :case, 'Synthetic lockbox. This is not a standing permission to enter.') ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-access"), "case": sid("phase20-case-access")},
    )
    connection.execute(
        text(
            "INSERT INTO maintenance_escalations (organization_id, id, case_id, step, recipient_role, state, human_acknowledged, fail_delivery, dedup_key) "
            "VALUES (:org, :id, :case, 0, 'technician', 'failed', false, true, :dedup) ON CONFLICT (organization_id, dedup_key) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-escalation-failed"), "case": sid("phase20-case-emergency"), "dedup": f"{sid('phase20-case-emergency')}:0"},
    )
    visit = sid("phase20-visit-complete")
    connection.execute(
        text(
            "INSERT INTO maintenance_visits (organization_id, id, case_id, actor_id, state) "
            "VALUES (:org, :id, :case, :actor, 'verified') ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": visit, "case": sid("phase20-case-complete"), "actor": technician},
    )
    for stage in ("before", "after"):
        connection.execute(
            text(
                "INSERT INTO maintenance_evidence (organization_id, id, case_id, visit_id, stage, caption, content_sha, scan_state, uploader_actor) "
                "VALUES (:org, :id, :case, :visit, :stage, :caption, :sha, 'available', :actor) ON CONFLICT (organization_id, id) DO NOTHING"
            ),
            {
                "org": organization,
                "id": sid(f"phase20-evidence-{stage}"),
                "case": sid("phase20-case-complete"),
                "visit": visit,
                "stage": stage,
                "caption": f"Synthetic {stage} photo of the same disposal fixture.",
                "sha": stage,
                "actor": technician,
            },
        )
    connection.execute(
        text(
            "INSERT INTO maintenance_reviews (organization_id, id, visit_id, submitter_actor, reviewer_actor, outcome, reason) "
            "VALUES (:org, :id, :visit, :submitter, :reviewer, 'verified', 'The after photo matches the requested disposal.') "
            "ON CONFLICT (organization_id, id) DO NOTHING"
        ),
        {"org": organization, "id": sid("phase20-review"), "visit": visit, "submitter": technician, "reviewer": coordinator},
    )

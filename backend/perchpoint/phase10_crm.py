"""Phase 10 leasing inquiries. Prospects stay separate from later application households.

This module does not schedule showings, collect applications, or score housing eligibility.
"""
from __future__ import annotations

import hashlib
import json
import re
from uuid import uuid4

from sqlalchemy import text

from .commands import CommandError, _audit_outbox, _command

PROHIBITED_TAGS = {"race", "religion", "family_status", "national_origin", "disability", "desirability", "screening", "income_score"}
STAGES = {"new", "assigned", "contact_attempted", "engaged", "next_step_ready", "nurture", "closed", "duplicate", "spam"}
ALLOWED = {
    ("new", "assigned"),
    ("new", "contact_attempted"),
    ("new", "closed"),
    ("assigned", "contact_attempted"),
    ("assigned", "closed"),
    ("contact_attempted", "engaged"),
    ("contact_attempted", "closed"),
    ("engaged", "next_step_ready"),
    ("engaged", "closed"),
    ("next_step_ready", "nurture"),
    ("next_step_ready", "closed"),
    ("nurture", "closed"),
    ("closed", "new"),
}
STAFF_SOURCES = {"phone", "walk_in", "forwarded"}


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized")


def _role(connection) -> str:
    return connection.execute(text("SELECT perchpoint.role_for_account(perchpoint.current_actor())")).scalar() or ""


def _clean(value: str) -> str:
    return re.sub(r"[<>]", "", value or "")[:500]


def capture_public(settings, body: dict, *, gpc: bool) -> dict:
    from .db import runtime_transaction

    allowed = ("name", "email", "phone", "message", "public_slug", "slugs", "disclosure", "honeypot", "marketing_opt_in", "fail_delivery", "search_ref", "position", "first_touch", "last_touch")
    forbidden = ("organization_id", "snapshot_id", "prospect_id", "lead_score", "tenant_quality", "attachment")
    payload = {key: body.get(key) for key in allowed if body.get(key) not in (None, "")}
    payload.update({key: body.get(key) for key in forbidden if body.get(key) not in (None, "")})
    if body.get("disclosure") is True:
        payload["disclosure"] = "true"
    if body.get("marketing_opt_in") is True:
        payload["marketing_opt_in"] = "true"
    if body.get("fail_delivery") is True:
        payload["fail_delivery"] = "true"
    fingerprint = hashlib.sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        result = connection.execute(
            text("SELECT perchpoint.capture_leasing_inquiry(CAST(:payload AS jsonb), :key, :fingerprint, :gpc)"),
            {"payload": json.dumps(payload), "key": body["idempotency_key"], "fingerprint": fingerprint, "gpc": gpc},
        ).scalar()
    if isinstance(result, str):
        result = json.loads(result)
    if not result.get("accepted"):
        code = result.get("code") or "rejected"
        status = 409 if code == "conflict" else 400
        raise CommandError(status, code, "The inquiry was not accepted")
    return {"receipt": result["receipt"], "replayed": bool(result.get("replayed")), "status": "received", "synthetic": True}


def record_staff(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        if body["source"] not in STAFF_SOURCES:
            raise CommandError(422, "source_rejected", "Staff entry cannot be labeled as a website inquiry")
        prospect = uuid4()
        inquiry = uuid4()
        receipt = uuid4().hex
        deadline = connection.execute(
            text("SELECT perchpoint.leasing_deadline(CAST(:received AS timestamptz), CAST(:org AS uuid))"),
            {"received": body["received_at"], "org": organization},
        ).scalar()
        connection.execute(
            text("INSERT INTO prospects (organization_id, id, display_name, kind) VALUES (:org, :id, :name, 'person')"),
            {"org": organization, "id": prospect, "name": body["name"]},
        )
        connection.execute(
            text(
                """
                INSERT INTO prospect_contacts (organization_id, id, prospect_id, kind, entered, normalized, verification, provenance)
                VALUES (:org, :id, :prospect, 'email', :entered, :normalized, 'unverified', :source)
                """
            ),
            {"org": organization, "id": uuid4(), "prospect": prospect, "entered": body["email"], "normalized": body["email"].lower(), "source": body["source"]},
        )
        connection.execute(
            text(
                """
                INSERT INTO leasing_inquiries (
                  organization_id, id, prospect_id, origin_prospect_id, public_receipt, source, stage, general_interest, received_at
                ) VALUES (:org, :id, :prospect, :prospect, :receipt, :source, 'new', true, CAST(:received AS timestamptz))
                """
            ),
            {"org": organization, "id": inquiry, "prospect": prospect, "receipt": receipt, "source": body["source"], "received": body["received_at"]},
        )
        connection.execute(
            text("INSERT INTO inquiry_stage_episodes (organization_id, id, inquiry_id, stage, reason) VALUES (:org, :id, :inquiry, 'new', 'staff_entry')"),
            {"org": organization, "id": uuid4(), "inquiry": inquiry},
        )
        connection.execute(
            text("INSERT INTO inquiry_assignments (organization_id, id, inquiry_id, reason) VALUES (:org, :id, :inquiry, 'awaiting_claim')"),
            {"org": organization, "id": uuid4(), "inquiry": inquiry},
        )
        connection.execute(
            text(
                """
                INSERT INTO inquiry_clocks (organization_id, id, inquiry_id, policy_version, zone_name, started_at, deadline_at)
                VALUES (:org, :id, :inquiry, 1, 'America/New_York', CAST(:received AS timestamptz), :deadline)
                """
            ),
            {"org": organization, "id": uuid4(), "inquiry": inquiry, "received": body["received_at"], "deadline": deadline},
        )
        connection.execute(
            text("INSERT INTO inquiry_actions (organization_id, id, inquiry_id, kind, status, is_primary, due_at) VALUES (:org, :id, :inquiry, 'review_inquiry', 'open', true, :due)"),
            {"org": organization, "id": uuid4(), "inquiry": inquiry, "due": deadline},
        )
        result = {"id": str(inquiry), "receipt": receipt, "source": body["source"], "deadline": deadline.isoformat(), "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.recorded", inquiry, correlation, "leasing.recorded.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.recorded", write)


def queue(settings, actor, organization, receipt: str | None = None) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, "inquiry.manage")
        rows = connection.execute(
            text(
                """
                SELECT inquiry.public_receipt, inquiry.stage, inquiry.version, assignment.account_id IS NULL AS unassigned,
                       clock.deadline_at, action.kind AS next_action
                FROM leasing_inquiries inquiry
                JOIN inquiry_assignments assignment ON assignment.organization_id = inquiry.organization_id AND assignment.inquiry_id = inquiry.id AND assignment.current
                JOIN inquiry_clocks clock ON clock.organization_id = inquiry.organization_id AND clock.inquiry_id = inquiry.id
                JOIN inquiry_actions action ON action.organization_id = inquiry.organization_id AND action.inquiry_id = inquiry.id AND action.is_primary AND action.status = 'open'
                WHERE (:receipt = '' OR inquiry.public_receipt = :receipt)
                ORDER BY clock.deadline_at, inquiry.public_receipt
                LIMIT 50
                """
            ),
            {"receipt": receipt or ""},
        ).mappings().all()
    return {"inquiries": [{**dict(row), "deadline_at": row["deadline_at"].isoformat(), "public_receipt": row["public_receipt"]} for row in rows], "synthetic": True}


def transition(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text("SELECT id, stage, version FROM leasing_inquiries WHERE organization_id = :org AND public_receipt = :receipt FOR UPDATE"),
            {"org": organization, "receipt": body["receipt"]},
        ).mappings().first()
        if not row:
            raise CommandError(404, "not_found", "Inquiry was not found")
        if int(row["version"]) != int(body["expected_version"]):
            raise CommandError(409, "conflict", "The inquiry changed. Reload and try again.", retryable=True)
        target = body["stage"]
        if target not in STAGES or (row["stage"], target) not in ALLOWED:
            raise CommandError(422, "transition_rejected", "That stage change is not available")
        if target == "closed" and not body.get("reason"):
            raise CommandError(422, "reason_required", "Closure needs an operational reason")
        connection.execute(
            text("UPDATE inquiry_stage_episodes SET current = false, ended_at = now() WHERE organization_id = :org AND inquiry_id = :id AND current"),
            {"org": organization, "id": row["id"]},
        )
        connection.execute(
            text("INSERT INTO inquiry_stage_episodes (organization_id, id, inquiry_id, stage, reason) VALUES (:org, :episode, :id, :stage, :reason)"),
            {"org": organization, "id": row["id"], "episode": uuid4(), "stage": target, "reason": body.get("reason") or ""},
        )
        connection.execute(
            text("UPDATE leasing_inquiries SET stage = :stage, version = version + 1 WHERE organization_id = :org AND id = :id"),
            {"org": organization, "stage": target, "id": row["id"]},
        )
        if target == "closed":
            connection.execute(
                text("UPDATE inquiry_actions SET status = 'done', is_primary = false WHERE organization_id = :org AND inquiry_id = :id AND status = 'open'"),
                {"org": organization, "id": row["id"]},
            )
        if target == "new" and row["stage"] == "closed":
            deadline = connection.execute(text("SELECT deadline_at FROM inquiry_clocks WHERE organization_id = :org AND inquiry_id = :id"), {"org": organization, "id": row["id"]}).scalar()
            connection.execute(
                text("INSERT INTO inquiry_actions (organization_id, id, inquiry_id, kind, status, is_primary, due_at) VALUES (:org, :action, :id, 'review_reopened', 'open', true, :due)"),
                {"org": organization, "action": uuid4(), "id": row["id"], "due": deadline},
            )
        result = {"receipt": body["receipt"], "stage": target, "version": int(row["version"]) + 1, "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.transitioned", row["id"], correlation, "leasing.transitioned.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.transitioned", write)


def claim(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text("SELECT id, version, stage FROM leasing_inquiries WHERE organization_id = :org AND public_receipt = :receipt FOR UPDATE"),
            {"org": organization, "receipt": body["receipt"]},
        ).mappings().first()
        if not row:
            raise CommandError(404, "not_found", "Inquiry was not found")
        if int(row["version"]) != int(body["expected_version"]):
            raise CommandError(409, "conflict", "The inquiry changed. Reload and try again.", retryable=True)
        connection.execute(
            text("UPDATE inquiry_assignments SET current = false WHERE organization_id = :org AND inquiry_id = :id AND current"),
            {"org": organization, "id": row["id"]},
        )
        connection.execute(
            text("INSERT INTO inquiry_assignments (organization_id, id, inquiry_id, account_id, reason) VALUES (:org, :assignment, :id, :actor, 'claimed')"),
            {"org": organization, "assignment": uuid4(), "id": row["id"], "actor": actor},
        )
        stage = "assigned" if row["stage"] == "new" else row["stage"]
        connection.execute(
            text("UPDATE leasing_inquiries SET stage = :stage, version = version + 1 WHERE organization_id = :org AND id = :id"),
            {"org": organization, "stage": stage, "id": row["id"]},
        )
        result = {"receipt": body["receipt"], "stage": stage, "version": int(row["version"]) + 1, "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.claimed", row["id"], correlation, "leasing.claimed.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.claimed", write)


def add_note(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        inquiry = connection.execute(
            text("SELECT id FROM leasing_inquiries WHERE organization_id = :org AND public_receipt = :receipt"),
            {"org": organization, "receipt": body["receipt"]},
        ).scalar()
        if not inquiry:
            raise CommandError(404, "not_found", "Inquiry was not found")
        note_id = uuid4()
        connection.execute(
            text("INSERT INTO leasing_notes (organization_id, id, inquiry_id, body, author_id) VALUES (:org, :id, :inquiry, :body, :actor)"),
            {"org": organization, "id": note_id, "inquiry": inquiry, "body": _clean(body["body"]), "actor": actor},
        )
        result = {"id": str(note_id), "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.note_added", note_id, correlation, "leasing.note_added.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.note_added", write)


def add_tag(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        if body["code"] in PROHIBITED_TAGS:
            raise CommandError(422, "tag_rejected", "That label is not an allowed operational tag")
        existing = connection.execute(
            text("SELECT id FROM leasing_tag_definitions WHERE organization_id = :org AND code = :code"),
            {"org": organization, "code": body["code"]},
        ).first()
        if existing:
            raise CommandError(409, "conflict", "That tag already exists")
        tag_id = uuid4()
        connection.execute(
            text("INSERT INTO leasing_tag_definitions (organization_id, id, code) VALUES (:org, :id, :code)"),
            {"org": organization, "id": tag_id, "code": body["code"]},
        )
        result = {"id": str(tag_id), "code": body["code"], "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.tag_defined", tag_id, correlation, "leasing.tag_defined.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.tag_defined", write)


def attempt_contact(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text(
                """
                SELECT inquiry.id, contact.suppressed
                FROM leasing_inquiries inquiry
                JOIN prospect_contacts contact ON contact.organization_id = inquiry.organization_id AND contact.prospect_id = inquiry.prospect_id
                WHERE inquiry.organization_id = :org AND inquiry.public_receipt = :receipt AND contact.kind = 'email'
                """
            ),
            {"org": organization, "receipt": body["receipt"]},
        ).mappings().first()
        if not row:
            raise CommandError(404, "not_found", "Inquiry was not found")
        if row["suppressed"]:
            raise CommandError(403, "suppressed", "That destination is suppressed")
        attempt_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO contact_attempts (organization_id, id, inquiry_id, channel, direction, outcome, suppressed, summary, actor_id)
                VALUES (:org, :id, :inquiry, 'email', 'outbound', :outcome, false, :summary, :actor)
                """
            ),
            {"org": organization, "id": attempt_id, "inquiry": row["id"], "outcome": body["outcome"], "summary": _clean(body["summary"]), "actor": actor},
        )
        connection.execute(
            text("UPDATE inquiry_clocks SET qualified_at = COALESCE(qualified_at, now()) WHERE organization_id = :org AND inquiry_id = :id"),
            {"org": organization, "id": row["id"]},
        )
        result = {"id": str(attempt_id), "qualified": True, "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.attempted", attempt_id, correlation, "leasing.attempted.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.attempted", write)


def suppress_contact(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        updated = connection.execute(
            text(
                """
                UPDATE prospect_contacts SET suppressed = true
                WHERE organization_id = :org AND normalized = :email
                RETURNING id
                """
            ),
            {"org": organization, "email": body["email"].lower()},
        ).first()
        if not updated:
            raise CommandError(404, "not_found", "Contact was not found")
        result = {"suppressed": True, "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.suppressed", updated.id, correlation, "leasing.suppressed.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.suppressed", write)


def merge_prospects(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        survivor = connection.execute(
            text("SELECT id, version FROM prospects WHERE organization_id = :org AND id = :id AND merged_into IS NULL"),
            {"org": organization, "id": body["survivor_id"]},
        ).mappings().first()
        alias = connection.execute(
            text("SELECT id, version FROM prospects WHERE organization_id = :org AND id = :id AND merged_into IS NULL"),
            {"org": organization, "id": body["alias_id"]},
        ).mappings().first()
        if not survivor or not alias:
            raise CommandError(404, "not_found", "Prospect was not found")
        if int(survivor["version"]) != int(body["expected_version"]):
            raise CommandError(409, "conflict", "The prospect changed. Reload and try again.", retryable=True)
        inquiries = connection.execute(
            text("SELECT count(*) FROM leasing_inquiries WHERE organization_id = :org AND prospect_id = :id"),
            {"org": organization, "id": alias["id"]},
        ).scalar()
        if body.get("dry_run"):
            return {"dry_run": True, "inquiries": int(inquiries or 0), "synthetic": True}
        connection.execute(
            text("UPDATE prospects SET merged_into = :survivor, version = version + 1 WHERE organization_id = :org AND id = :alias"),
            {"org": organization, "survivor": survivor["id"], "alias": alias["id"]},
        )
        connection.execute(
            text("UPDATE leasing_inquiries SET prospect_id = :survivor WHERE organization_id = :org AND prospect_id = :alias"),
            {"org": organization, "survivor": survivor["id"], "alias": alias["id"]},
        )
        connection.execute(
            text("UPDATE prospects SET version = version + 1 WHERE organization_id = :org AND id = :id"),
            {"org": organization, "id": survivor["id"]},
        )
        merge_id = uuid4()
        connection.execute(
            text("INSERT INTO prospect_merges (organization_id, id, survivor_id, alias_id, reason, actor_id) VALUES (:org, :id, :survivor, :alias, :reason, :actor)"),
            {"org": organization, "id": merge_id, "survivor": survivor["id"], "alias": alias["id"], "reason": body["reason"], "actor": actor},
        )
        result = {"id": str(merge_id), "inquiries": int(inquiries or 0), "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.merged", merge_id, correlation, "leasing.merged.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.merged", write)


def unmerge_prospect(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "inquiry.manage")
        alias = connection.execute(
            text("SELECT id, merged_into FROM prospects WHERE organization_id = :org AND id = :id"),
            {"org": organization, "id": body["alias_id"]},
        ).mappings().first()
        if not alias or not alias["merged_into"]:
            raise CommandError(422, "unmerge_rejected", "That prospect is not merged")
        connection.execute(
            text("UPDATE leasing_inquiries SET prospect_id = origin_prospect_id WHERE organization_id = :org AND origin_prospect_id = :alias"),
            {"org": organization, "alias": alias["id"]},
        )
        connection.execute(
            text("UPDATE prospects SET merged_into = NULL, version = version + 1 WHERE organization_id = :org AND id = :id"),
            {"org": organization, "id": alias["id"]},
        )
        result = {"alias_id": str(alias["id"]), "synthetic": True}
        _audit_outbox(connection, organization, actor, "leasing.unmerged", alias["id"], correlation, "leasing.unmerged.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "leasing.unmerged", write)


def detail(settings, actor, organization, receipt: str) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text(
                """
                SELECT inquiry.id, inquiry.prospect_id, inquiry.source, inquiry.stage, inquiry.version,
                       inquiry.general_interest, clock.qualified_at, clock.deadline_at, action.kind AS next_action
                FROM leasing_inquiries inquiry
                JOIN inquiry_clocks clock ON clock.organization_id = inquiry.organization_id AND clock.inquiry_id = inquiry.id
                LEFT JOIN inquiry_actions action ON action.organization_id = inquiry.organization_id
                  AND action.inquiry_id = inquiry.id AND action.is_primary AND action.status = 'open'
                WHERE inquiry.organization_id = :org AND inquiry.public_receipt = :receipt
                """
            ),
            {"org": organization, "receipt": receipt},
        ).mappings().first()
        if not row:
            raise CommandError(404, "not_found", "Inquiry was not found")
        consents = connection.execute(
            text("SELECT purpose, status FROM prospect_consents WHERE organization_id = :org AND prospect_id = :prospect"),
            {"org": organization, "prospect": row["prospect_id"]},
        ).mappings().all()
        interests = connection.execute(
            text("SELECT public_slug, availability_state, snapshot_id IS NOT NULL AS has_snapshot FROM leasing_interests WHERE organization_id = :org AND inquiry_id = :id"),
            {"org": organization, "id": row["id"]},
        ).mappings().all()
        attribution = connection.execute(
            text("SELECT direct_source, first_touch, last_touch, gpc FROM leasing_attributions WHERE organization_id = :org AND inquiry_id = :id"),
            {"org": organization, "id": row["id"]},
        ).mappings().first()
        candidates = connection.execute(
            text("SELECT reason_code FROM duplicate_candidates WHERE organization_id = :org AND (left_prospect = :prospect OR right_prospect = :prospect)"),
            {"org": organization, "prospect": row["prospect_id"]},
        ).scalars().all()
    return {
        "prospect_id": str(row["prospect_id"]),
        "source": row["source"],
        "stage": row["stage"],
        "version": int(row["version"]),
        "general_interest": bool(row["general_interest"]),
        "qualified": row["qualified_at"] is not None,
        "deadline_at": row["deadline_at"].isoformat(),
        "next_action": row["next_action"],
        "consents": [dict(item) for item in consents],
        "interests": [dict(item) for item in interests],
        "attribution": dict(attribution) if attribution else None,
        "candidate_reasons": list(candidates),
        "synthetic": True,
    }


def metrics(settings, actor, organization) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, "inquiry.manage")
        counts = connection.execute(
            text(
                """
                SELECT
                  count(*) AS intake,
                  count(*) FILTER (WHERE assignment.account_id IS NULL AND inquiry.stage <> 'closed') AS unassigned,
                  count(*) FILTER (WHERE clock.qualified_at IS NOT NULL) AS human_responses
                FROM leasing_inquiries inquiry
                JOIN inquiry_assignments assignment ON assignment.organization_id = inquiry.organization_id AND assignment.inquiry_id = inquiry.id AND assignment.current
                JOIN inquiry_clocks clock ON clock.organization_id = inquiry.organization_id AND clock.inquiry_id = inquiry.id
                """
            )
        ).mappings().one()
    return {
        "intake": int(counts["intake"] or 0),
        "unassigned": int(counts["unassigned"] or 0),
        "human_responses": int(counts["human_responses"] or 0),
        "receipts_are_not_responses": True,
        "showing_conversion": None,
        "synthetic": True,
    }


def owner_summary(settings, actor, organization) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, "approval.owner")
        if _role(connection) != "owner":
            raise CommandError(403, "owner_reserved", "The owner summary is reserved")
        total = connection.execute(text("SELECT count(*) FROM leasing_inquiries")).scalar()
    return {"intake": int(total or 0), "names_included": False, "synthetic": True}

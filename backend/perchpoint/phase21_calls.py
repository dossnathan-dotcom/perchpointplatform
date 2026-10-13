"""Phase 21 call metadata. No audio, transcript, or money movement is stored."""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from twilio.request_validator import RequestValidator

from .commands import CommandError
from .db import application_admin_connection, runtime_transaction
from .settings import Settings

PROPERTY_ZONE = ZoneInfo("America/New_York")
FORBIDDEN_FIELDS = (
    "RecordingUrl",
    "RecordingSid",
    "TranscriptionText",
    "TranscriptionSid",
    "MediaUrl",
    "CallRecording",
)
TOKEN_ENV = "PHASE21_PROVIDER_TOKEN"
DEFAULT_TOKEN = "local-only-not-production-call-token"
DEFAULT_EDGES = (
    ("inbound", "ann-handset"),
    ("emergency", "on-call"),
    ("on-call", "owner"),
)


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def _require(connection, capability: str) -> None:
    allowed = connection.execute(
        text("SELECT perchpoint.has_capability(:capability)"),
        {"capability": capability},
    ).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _journals(connection) -> int:
    return int(connection.execute(text("SELECT count(*) FROM journal_transactions")).scalar_one())


def _fingerprint(parts: list[str]) -> str:
    return hashlib.sha256("|".join(parts).encode()).hexdigest()


def _reference() -> str:
    return "PP-C21-" + uuid4().hex[:8].upper()


def provider_token() -> str:
    configured = os.environ.get(TOKEN_ENV)
    if configured:
        return configured
    if os.environ.get("PHASE3_ENVIRONMENT", "local") in {"local", "test"}:
        return DEFAULT_TOKEN
    raise CommandError(503, "unavailable", "The call provider token is not configured.", False)


def recording_posture() -> dict:
    return {"recording": False, "transcription": False, "media_stream": False, "money_moved": False}


def graph_has_loop(edges: list[tuple[str, str]]) -> bool:
    graph: dict[str, list[str]] = {}
    for source, destination in edges:
        graph.setdefault(source, []).append(destination)

    def visit(node: str, stack: set[str]) -> bool:
        if node in stack:
            return True
        stack.add(node)
        for nxt in graph.get(node, []):
            if visit(nxt, stack):
                return True
        stack.remove(node)
        return False

    return any(visit(node, set()) for node in list(graph))


def _edges(raw: object) -> list[tuple[str, str]]:
    if not isinstance(raw, list):
        raise CommandError(400, "invalid", "The routing graph needs a list of steps.", False)
    edges: list[tuple[str, str]] = []
    for item in raw:
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise CommandError(400, "invalid", "Each routing step needs a source and a destination.", False)
        edges.append((str(item[0]), str(item[1])))
    if graph_has_loop(edges):
        raise CommandError(409, "loop", "That forwarding path would loop and was not saved.", False)
    return edges


def _business_hours(moment: datetime) -> bool:
    local = moment.astimezone(PROPERTY_ZONE)
    return local.weekday() < 5 and 9 <= local.hour < 17


def _destination(moment: datetime, digits: str, emergency: bool) -> str:
    if emergency or digits == "9":
        return "on-call"
    if _business_hours(moment):
        return "ann-handset"
    return "callback-task"


def desk(settings: Settings, actor, organization) -> dict:
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "calls.coordinate")
        rows = connection.execute(
            text(
                "SELECT public_reference, mode, direction, caller_status, subject_kind, case_reference, "
                "terminal_outcome, human_acknowledged, duration_seconds, duration_kind, duration_source, "
                "callback_due_at, repeat_count, created_at FROM call_interactions "
                "ORDER BY created_at DESC LIMIT 50"
            )
        ).mappings().all()
        callbacks = connection.execute(
            text(
                "SELECT interaction.public_reference, callback.state, callback.due_at, callback.reason "
                "FROM call_callbacks callback JOIN call_interactions interaction "
                "ON interaction.id = callback.interaction_id WHERE callback.state <> 'done' "
                "ORDER BY callback.due_at"
            )
        ).mappings().all()
    return {
        "items": [dict(row) for row in rows],
        "callbacks": [dict(row) for row in callbacks],
        "recording": False,
        "money_moved": False,
        "real_values_activated": False,
    }


def save_route(settings: Settings, actor, organization, body: dict) -> dict:
    edges = _edges(body.get("edges") or [list(item) for item in DEFAULT_EDGES])
    account_sid = str(body.get("account_sid") or "AC-local-synthetic")
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "calls.coordinate")
        before = _journals(connection)
        connection.execute(
            text(
                "INSERT INTO call_routes (organization_id, ann_destination, emergency_digit, edges) "
                "VALUES (:org, 'ann-handset', '9', CAST(:edges AS jsonb)) "
                "ON CONFLICT (organization_id) DO UPDATE SET edges = EXCLUDED.edges, updated_at = now()"
            ),
            {"org": _org(organization), "edges": json.dumps(edges)},
        )
        bound = connection.execute(
            text(
                "INSERT INTO call_provider_accounts (organization_id, id, account_sid, environment) "
                "VALUES (:org, :id, :sid, 'local') ON CONFLICT (account_sid, environment) DO NOTHING "
                "RETURNING organization_id"
            ),
            {"org": _org(organization), "id": uuid4(), "sid": account_sid},
        ).scalar()
        if bound is None:
            owner = connection.execute(
                text(
                    "SELECT organization_id FROM call_provider_accounts "
                    "WHERE account_sid = :sid AND environment = 'local'"
                ),
                {"sid": account_sid},
            ).scalar()
            if owner != _org(organization):
                raise CommandError(409, "conflict", "That provider account is already bound.", False)
        if _journals(connection) != before:
            raise CommandError(409, "money", "A call route cannot change the ledger.", False)
    return {"accepted": True, "loop": False, "recording": False, "money_moved": False}


def record_manual(settings: Settings, actor, organization, body: dict) -> dict:
    description = str(body.get("description") or "").strip()
    if not description:
        raise CommandError(400, "invalid", "A manual call needs what was said.", False)
    source = str(body.get("duration_source") or "unknown")
    if source not in {"manual", "unknown"}:
        raise CommandError(400, "invalid", "Duration must be manual or unknown.", False)
    seconds = body.get("duration_seconds")
    if source == "unknown" and seconds not in (None, ""):
        raise CommandError(400, "invalid", "Unknown duration cannot also carry a number.", False)
    if source == "manual" and seconds is None:
        raise CommandError(400, "invalid", "A manual duration needs the reported seconds.", False)
    key = str(body.get("idempotency_key") or "")
    fingerprint = _fingerprint([description, source, str(seconds)])
    reference = _reference()
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "calls.coordinate")
        existing = connection.execute(
            text(
                "SELECT fingerprint, public_reference FROM call_commands "
                "WHERE actor_id = perchpoint.current_actor() AND idempotency_key = :key"
            ),
            {"key": key},
        ).first()
        if existing is not None:
            if existing.fingerprint != fingerprint:
                raise CommandError(409, "conflict", "That call record changed and was not accepted.", False)
            return {"accepted": True, "reference": existing.public_reference, "replayed": True, "money_moved": False}
        before = _journals(connection)
        interaction_id = uuid4()
        connection.execute(
            text(
                "INSERT INTO call_interactions (organization_id, id, public_reference, mode, direction, "
                "caller_hint, caller_status, subject_kind, terminal_outcome, duration_seconds, duration_kind, "
                "duration_source, environment, money_moved, real_values_activated) "
                "VALUES (:org, :id, :reference, 'unintegrated', 'manual', :hint, 'unverified', 'unclassified', "
                "'recorded', :seconds, CASE WHEN :source = 'manual' THEN 'manual' ELSE NULL END, :source, "
                "'local', false, false)"
            ),
            {
                "org": _org(organization),
                "id": interaction_id,
                "reference": reference,
                "hint": str(body.get("caller_hint") or ""),
                "seconds": int(str(body.get("duration_seconds"))) if source == "manual" else None,
                "source": source,
            },
        )
        connection.execute(
            text(
                "INSERT INTO call_notes (organization_id, id, interaction_id, author_actor, body) "
                "VALUES (:org, :id, :interaction, perchpoint.current_actor(), :body)"
            ),
            {"org": _org(organization), "id": uuid4(), "interaction": interaction_id, "body": description},
        )
        connection.execute(
            text(
                "INSERT INTO call_commands (organization_id, actor_id, idempotency_key, fingerprint, public_reference) "
                "VALUES (:org, perchpoint.current_actor(), :key, :fingerprint, :reference)"
            ),
            {"org": _org(organization), "key": key, "fingerprint": fingerprint, "reference": reference},
        )
        if _journals(connection) != before:
            raise CommandError(409, "money", "A call record cannot change the ledger.", False)
    return {
        "accepted": True,
        "reference": reference,
        "replayed": False,
        "connected_proof": False,
        "money_moved": False,
    }


def _strip(params: dict) -> tuple[dict, list[str]]:
    clean: dict[str, str] = {}
    rejected: list[str] = []
    for key, value in params.items():
        blocked = any(key == name or key.startswith(name) for name in FORBIDDEN_FIELDS)
        if blocked or str(value).lower() in {"record", "transcribe"}:
            rejected.append(key)
            continue
        clean[key] = str(value)
    return clean, rejected


def _signature_ok(url: str, params: dict, signature: str) -> bool:
    if not signature:
        return False
    validator = RequestValidator(provider_token())
    signed = {key: str(value) for key, value in params.items()}
    return bool(validator.validate(url, signed, signature))


def apply_provider_event(settings: Settings, url: str, params: dict, signature: str) -> dict:
    if not _signature_ok(url, params, signature):
        raise CommandError(401, "denied", "The provider signature was not accepted.", False)
    if str(params.get("record") or "").lower() in {"true", "1"} or params.get("transcribe"):
        raise CommandError(409, "recording", "Recording and transcription stay off.", False)
    clean, rejected = _strip(params)
    account_sid = clean.get("AccountSid", "")
    event_id = clean.get("CallEventId") or f"{clean.get('CallSid', '')}:{clean.get('SequenceNumber', '0')}:{clean.get('CallStatus', '')}"
    if not account_sid or not clean.get("CallSid"):
        raise CommandError(400, "invalid", "The provider event is missing the call identity.", False)
    sequence = int(clean.get("SequenceNumber") or 0)
    status = clean.get("CallStatus", "unknown")
    answered_by = clean.get("AnsweredBy", "")
    outcome = "voicemail" if answered_by in {"machine", "machine_start", "fax"} else {
        "completed": "connected",
        "busy": "busy",
        "no-answer": "no-answer",
        "canceled": "cancelled",
        "failed": "rejected",
    }.get(status, status)
    occurred = datetime.now(timezone.utc)
    if clean.get("Timestamp"):
        occurred = datetime.fromisoformat(clean["Timestamp"])
        if occurred.tzinfo is None:
            occurred = occurred.replace(tzinfo=timezone.utc)
    digits = clean.get("Digits", "")
    emergency = clean.get("Emergency") == "true" or digits == "9"
    destination = _destination(occurred, digits, emergency)
    root = clean.get("ParentCallSid") or clean["CallSid"]
    with application_admin_connection(settings) as connection:
        organization = connection.execute(
            text(
                "SELECT organization_id FROM call_provider_accounts "
                "WHERE account_sid = :sid AND environment = 'local'"
            ),
            {"sid": account_sid},
        ).scalar()
        if organization is None:
            raise CommandError(404, "missing", "That provider account is not bound to this organization.", False)
        before = _journals(connection)
        duplicate = connection.execute(
            text("SELECT 1 FROM call_events WHERE organization_id = :org AND provider_event_id = :event"),
            {"org": organization, "event": event_id},
        ).first()
        if duplicate is not None:
            return {"accepted": True, "replayed": True, "human_acknowledged": False, "money_moved": False}
        existing = connection.execute(
            text(
                "SELECT id, public_reference, latest_sequence, terminal_outcome, repeat_count "
                "FROM call_interactions WHERE organization_id = :org AND root_sid = :root"
            ),
            {"org": organization, "root": root},
        ).mappings().first()
        interaction_id = existing["id"] if existing else uuid4()
        reference = existing["public_reference"] if existing else _reference()
        latest = int(str(existing["latest_sequence"] or 0)) if existing else -1
        stale = sequence < latest and existing and existing["terminal_outcome"]
        if existing is None:
            connection.execute(
                text(
                    "INSERT INTO call_interactions (organization_id, id, public_reference, mode, direction, root_sid, "
                    "caller_hint, caller_status, terminal_outcome, duration_kind, duration_source, duration_seconds, "
                    "latest_sequence, environment, money_moved, real_values_activated) "
                    "VALUES (:org, :id, :reference, 'integrated', 'inbound', :root, :hint, :caller_status, :outcome, "
                    ":duration_kind, 'provider', :duration_seconds, :sequence, 'local', false, false)"
                ),
                _interaction_values(organization, interaction_id, reference, root, clean, outcome, sequence),
            )
        elif not stale:
            connection.execute(
                text(
                    "UPDATE call_interactions SET terminal_outcome = :outcome, latest_sequence = :sequence, "
                    "duration_kind = :duration_kind, duration_source = 'provider', duration_seconds = :duration_seconds, "
                    "repeat_count = repeat_count + 1 WHERE id = :id"
                ),
                {**_duration(clean), "outcome": outcome, "sequence": sequence, "id": interaction_id},
            )
        connection.execute(
            text(
                "INSERT INTO call_legs (organization_id, id, interaction_id, provider_leg_id, destination_label, outcome, "
                "ringing_seconds, connected_seconds, billed_seconds) VALUES "
                "(:org, :id, :interaction, :leg, :destination, :outcome, :ringing, :connected, :billed) "
                "ON CONFLICT (organization_id, provider_leg_id) DO UPDATE SET outcome = EXCLUDED.outcome, "
                "connected_seconds = EXCLUDED.connected_seconds, billed_seconds = EXCLUDED.billed_seconds"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "interaction": interaction_id,
                "leg": clean["CallSid"],
                "destination": destination,
                "outcome": outcome,
                "ringing": _optional_int(clean.get("RingingDuration")),
                "connected": _optional_int(clean.get("DialCallDuration")),
                "billed": _optional_int(clean.get("CallDuration")),
            },
        )
        connection.execute(
            text(
                "INSERT INTO call_events (organization_id, id, interaction_id, provider_event_id, event_name, sequence, occurred_at) "
                "VALUES (:org, :id, :interaction, :event, :name, :sequence, :occurred)"
            ),
            {
                "org": organization,
                "id": uuid4(),
                "interaction": interaction_id,
                "event": event_id,
                "name": status,
                "sequence": sequence,
                "occurred": occurred,
            },
        )
        for field_name in rejected:
            connection.execute(
                text(
                    "INSERT INTO call_rejections (organization_id, id, interaction_id, field_name, reason) "
                    "VALUES (:org, :id, :interaction, :field, 'recording or transcript field dropped')"
                ),
                {"org": organization, "id": uuid4(), "interaction": interaction_id, "field": field_name},
            )
        if outcome in {"busy", "no-answer", "cancelled", "rejected", "voicemail"} or destination == "callback-task":
            open_callback = connection.execute(
                text("SELECT 1 FROM call_callbacks WHERE interaction_id = :id AND state = 'open'"),
                {"id": interaction_id},
            ).first()
            if open_callback is None:
                connection.execute(
                    text(
                        "INSERT INTO call_callbacks (organization_id, id, interaction_id, owner_actor, due_at, state, reason) "
                        "SELECT :org, :callback_id, :interaction, account_id, :due, 'open', :reason FROM memberships "
                        "WHERE organization_id = :org AND role_name = 'operations_manager' "
                        "AND (ended_at IS NULL OR ended_at > now()) ORDER BY effective_at LIMIT 1"
                    ),
                    {
                        "org": organization,
                        "callback_id": uuid4(),
                        "interaction": interaction_id,
                        "due": occurred + timedelta(hours=2),
                        "reason": "Callback from an unanswered or after-hours call",
                    },
                )
                connection.execute(
                    text("UPDATE call_interactions SET callback_due_at = :due WHERE id = :id"),
                    {"due": occurred + timedelta(hours=2), "id": interaction_id},
                )
        if _journals(connection) != before:
            raise CommandError(409, "money", "A call event cannot change the ledger.", False)
    return {
        "accepted": True,
        "replayed": False,
        "reference": reference,
        "outcome": outcome,
        "destination": destination,
        "human_acknowledged": False,
        "rejected_fields": rejected,
        "money_moved": False,
    }


def _optional_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    return int(str(value))


def _duration(clean: dict) -> dict:
    if clean.get("DialCallDuration") not in (None, ""):
        return {"duration_kind": "connected", "duration_seconds": int(clean["DialCallDuration"])}
    if clean.get("CallDuration") not in (None, ""):
        return {"duration_kind": "billed", "duration_seconds": int(clean["CallDuration"])}
    if clean.get("RingingDuration") not in (None, ""):
        return {"duration_kind": "ringing", "duration_seconds": int(clean["RingingDuration"])}
    return {"duration_kind": None, "duration_seconds": None}


def _interaction_values(organization, interaction_id, reference, root, clean, outcome, sequence) -> dict:
    hint = clean.get("From") or ""
    status = "withheld" if hint.lower() in {"", "anonymous", "restricted"} else "unverified"
    duration = _duration(clean)
    return {
        "org": organization,
        "id": interaction_id,
        "reference": reference,
        "root": root,
        "hint": hint,
        "caller_status": status,
        "outcome": outcome,
        "sequence": sequence,
        **duration,
    }


def acknowledge(settings: Settings, actor, organization, reference: str) -> dict:
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "calls.coordinate")
        row = connection.execute(
            text("SELECT id, terminal_outcome, human_acknowledged FROM call_interactions WHERE public_reference = :reference"),
            {"reference": reference},
        ).mappings().first()
        if row is None:
            raise CommandError(404, "missing", "That call was not found.", False)
        if row["terminal_outcome"] == "voicemail":
            raise CommandError(409, "voicemail", "A carrier voicemail answer is not a person's acceptance.", False)
        if row["terminal_outcome"] != "connected":
            raise CommandError(409, "not_connected", "Acceptance requires a connected call, not only a dial.", False)
        connection.execute(
            text(
                "UPDATE call_interactions SET human_acknowledged = true, acknowledged_by = perchpoint.current_actor() "
                "WHERE id = :id"
            ),
            {"id": row["id"]},
        )
    return {"accepted": True, "human_acknowledged": True, "case_accepted": False, "money_moved": False}


def add_note(settings: Settings, actor, organization, body: dict) -> dict:
    return _mutate_note(settings, actor, organization, body, "note")


def link_case(settings: Settings, actor, organization, body: dict) -> dict:
    reference = str(body.get("reference") or "")
    case_reference = str(body.get("case_reference") or "")
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "calls.coordinate")
        updated = connection.execute(
            text(
                "UPDATE call_interactions SET case_reference = :case, subject_kind = 'maintenance' "
                "WHERE public_reference = :reference RETURNING id"
            ),
            {"case": case_reference, "reference": reference},
        ).first()
        if updated is None:
            raise CommandError(404, "missing", "That call was not found.", False)
    return {"accepted": True, "case_reference": case_reference, "money_moved": False}


def schedule_callback(settings: Settings, actor, organization, body: dict) -> dict:
    reference = str(body.get("reference") or "")
    due = datetime.fromisoformat(str(body.get("due_at")))
    if due.tzinfo is None:
        due = due.replace(tzinfo=timezone.utc)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "calls.coordinate")
        row = connection.execute(
            text("SELECT id FROM call_interactions WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "missing", "That call was not found.", False)
        connection.execute(
            text(
                "INSERT INTO call_callbacks (organization_id, id, interaction_id, owner_actor, due_at, state, reason) "
                "VALUES (:org, :id, :interaction, perchpoint.current_actor(), :due, 'open', :reason)"
            ),
            {
                "org": _org(organization),
                "id": uuid4(),
                "interaction": row.id,
                "due": due,
                "reason": str(body.get("reason") or "Staff scheduled a callback"),
            },
        )
        connection.execute(
            text("UPDATE call_interactions SET callback_due_at = :due WHERE id = :id"),
            {"due": due, "id": row.id},
        )
    return {"accepted": True, "owner": "current", "money_moved": False}


def review_caller(settings: Settings, actor, organization, body: dict) -> dict:
    status = str(body.get("caller_status") or "")
    if status not in {"unverified", "matched", "withheld", "ambiguous"}:
        raise CommandError(400, "invalid", "That caller status is not available.", False)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "calls.coordinate")
        updated = connection.execute(
            text("UPDATE call_interactions SET caller_status = :status WHERE public_reference = :reference RETURNING id"),
            {"status": status, "reference": body.get("reference")},
        ).first()
        if updated is None:
            raise CommandError(404, "missing", "That call was not found.", False)
    return {"accepted": True, "caller_status": status, "household_disclosed": False, "money_moved": False}


def _mutate_note(settings, actor, organization, body: dict, kind: str) -> dict:
    reference = str(body.get("reference") or "")
    note = str(body.get("body") or "").strip()
    if not note:
        raise CommandError(400, "invalid", "The note needs text.", False)
    with runtime_transaction(settings, _org(actor), _org(organization), uuid4()) as connection:
        _require(connection, "calls.coordinate")
        row = connection.execute(
            text("SELECT id FROM call_interactions WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "missing", "That call was not found.", False)
        connection.execute(
            text(
                "INSERT INTO call_notes (organization_id, id, interaction_id, author_actor, body) "
                "VALUES (:org, :id, :interaction, perchpoint.current_actor(), :body)"
            ),
            {"org": _org(organization), "id": uuid4(), "interaction": row.id, "body": note},
        )
    return {"accepted": True, "kind": kind, "money_moved": False}


def process_callbacks(settings: Settings) -> dict:
    from .phase6_identity import authenticate_service_credential

    principal = authenticate_service_credential(
        settings,
        os.environ.get("PHASE6_WORKER_CREDENTIAL", "local-only-not-production-worker-credential"),
        audience="perchpoint-worker",
        worker_name=os.environ.get("PHASE6_WORKER_NAME", "synthetic-worker"),
    )
    if principal is None:
        raise CommandError(401, "service_credential_invalid", "Worker authentication failed.", False)
    with runtime_transaction(settings, principal["id"], principal["organization_id"], uuid4()) as connection:
        row = connection.execute(
            text(
                "SELECT id FROM call_callbacks WHERE state = 'open' AND due_at < now() "
                "ORDER BY due_at FOR UPDATE SKIP LOCKED LIMIT 1"
            )
        ).first()
        if row is None:
            return {"applied": 0, "claimed": False}
        connection.execute(
            text("UPDATE call_callbacks SET state = 'escalated', reason = reason || ' Escalated to the owner.' WHERE id = :id"),
            {"id": row.id},
        )
        if os.environ.get("PHASE3_ENVIRONMENT", "local") in {"local", "test"} and os.environ.get("PHASE21_FAULT") == "before_commit":
            raise RuntimeError("injected fault")
    return {"applied": 1, "claimed": True, "human_acknowledged": False}


def seed_demo_calls(connection, organization, coordinator) -> None:
    if connection.execute(text("SELECT to_regclass('public.call_interactions')")).scalar() is None:
        return
    exists = connection.execute(
        text("SELECT 1 FROM call_interactions WHERE public_reference = 'PP-C21-MISSED'")
    ).first()
    if exists is not None:
        return
    interaction_id = uuid4()
    connection.execute(
        text(
            "INSERT INTO call_provider_accounts (organization_id, id, account_sid, environment) "
            "VALUES (:org, :id, 'AC-local-synthetic', 'local') ON CONFLICT (account_sid, environment) DO NOTHING"
        ),
        {"org": organization, "id": uuid4()},
    )
    connection.execute(
        text(
            "INSERT INTO call_routes (organization_id, edges) VALUES (:org, CAST(:edges AS jsonb)) "
            "ON CONFLICT (organization_id) DO NOTHING"
        ),
        {"org": organization, "edges": json.dumps([list(item) for item in DEFAULT_EDGES])},
    )
    connection.execute(
        text(
            "INSERT INTO call_interactions (organization_id, id, public_reference, mode, direction, caller_hint, "
            "caller_status, subject_kind, terminal_outcome, human_acknowledged, duration_source, environment, "
            "money_moved, real_values_activated) "
            "VALUES (:org, :id, 'PP-C21-MISSED', 'integrated', 'inbound', 'anonymous', 'withheld', 'unclassified', "
            "'no-answer', false, 'unknown', 'local', false, false)"
        ),
        {"org": organization, "id": interaction_id},
    )
    connection.execute(
        text(
            "INSERT INTO call_callbacks (organization_id, id, interaction_id, owner_actor, due_at, state, reason) "
            "VALUES (:org, :id, :interaction, :owner, now() - interval '1 hour', 'open', 'Missed synthetic call')"
        ),
        {"org": organization, "id": uuid4(), "interaction": interaction_id, "owner": coordinator},
    )

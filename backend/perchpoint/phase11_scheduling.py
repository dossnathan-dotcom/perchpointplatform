"""Phase 11 showing scheduling. PerchPoint is canonical; provider calendars are busy mirrors."""
from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError

from .commands import CommandError
from .db import runtime_transaction
from .settings import Settings

DURATION = timedelta(minutes=30)
BUFFER = timedelta(minutes=15)
LEAD = timedelta(hours=2)
STEP = timedelta(minutes=15)


def _minutes(value: datetime) -> int:
    offset = value.utcoffset()
    if offset is None:
        raise CommandError(422, "offset_mismatch", "The offset does not match the property zone.", False)
    return int(offset.total_seconds() // 60)


def _org(value: UUID | str) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


def resolve_wall(wall: str, zone: str, offset_minutes: int) -> datetime:
    naive = datetime.fromisoformat(wall)
    if naive.tzinfo is not None:
        raise CommandError(422, "invalid_wall", "Send property-local time without an offset.", False)
    tz = ZoneInfo(zone)
    early = naive.replace(tzinfo=tz, fold=0)
    late = naive.replace(tzinfo=tz, fold=1)
    early_offset = _minutes(early)
    late_offset = _minutes(late)
    early_exists = early.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == naive
    late_exists = late.astimezone(timezone.utc).astimezone(tz).replace(tzinfo=None) == naive
    if not early_exists and not late_exists:
        raise CommandError(422, "nonexistent_time", "That local time does not exist.", False)
    if early_exists and late_exists and early_offset != late_offset:
        chosen = early if offset_minutes == early_offset else late if offset_minutes == late_offset else None
        if chosen is None:
            raise CommandError(422, "ambiguous_time", "Choose an offset for the repeated local time.", False)
        return chosen
    chosen = early if early_exists else late
    actual = _minutes(chosen)
    if actual != offset_minutes:
        raise CommandError(422, "offset_mismatch", "The offset does not match the property zone.", False)
    return chosen


def candidate_slots(day: str, busy: list[dict], now: datetime | None = None) -> list[dict]:
    zone = ZoneInfo("America/New_York")
    start_day = datetime.fromisoformat(day).replace(tzinfo=zone)
    clock = now or datetime.now(timezone.utc)
    slots = []
    cursor = start_day.replace(hour=10, minute=0, second=0, microsecond=0)
    close = start_day.replace(hour=16, minute=0)
    while cursor + DURATION <= close:
        if cursor.astimezone(timezone.utc) >= clock + LEAD and cursor.date() <= (clock.astimezone(zone).date() + timedelta(days=30)):
            occupied_start = cursor - BUFFER
            occupied_end = cursor + DURATION + BUFFER
            blocked = False
            for span in busy:
                start = datetime.fromisoformat(span["start"])
                end = datetime.fromisoformat(span["end"])
                if start.tzinfo is None:
                    start = start.replace(tzinfo=timezone.utc)
                if end.tzinfo is None:
                    end = end.replace(tzinfo=timezone.utc)
                if occupied_start.astimezone(timezone.utc) < end and occupied_end.astimezone(timezone.utc) > start:
                    blocked = True
                    break
            if not blocked:
                slots.append({
                    "wall_start": cursor.replace(tzinfo=None).isoformat(timespec="minutes"),
                    "zone_name": "America/New_York",
                    "offset_minutes": _minutes(cursor),
                    "duration_minutes": 30,
                })
        cursor += STEP
    return slots


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized.", False)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()
    return hashlib.sha256(value.encode()).hexdigest()


def issue_capability(settings: Settings, receipt: str) -> dict:
    token = secrets.token_urlsafe(32)
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(
            text("SELECT perchpoint.issue_showing_capability(CAST(:receipt AS text), CAST(:token_hash AS text))"),
            {"receipt": receipt, "token_hash": _hash(token)},
        ).scalar_one()
    if not row["accepted"]:
        raise CommandError(400, "rejected", "The showing request could not be accepted.", False)
    return {"capability": token}


def slots_for(settings: Settings, capability: str, day: str) -> dict:
    zone = ZoneInfo("America/New_York")
    start = datetime.fromisoformat(day).replace(tzinfo=zone)
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(
            text("SELECT perchpoint.showing_busy(CAST(:token_hash AS text), CAST(:start AS timestamptz), CAST(:end AS timestamptz))"),
            {"token_hash": _hash(capability), "start": start, "end": start + timedelta(days=1)},
        ).scalar_one()
    if not row["accepted"]:
        raise CommandError(400, "rejected", "The showing request could not be accepted.", False)
    return {"slots": candidate_slots(day, row["spans"])}


def book(settings: Settings, payload: dict, idempotency_key: str) -> dict:
    if payload.get("mode") == "self_guided" or payload.get("access_code") or payload.get("lockbox"):
        raise CommandError(400, "rejected", "The showing request could not be accepted.", False)
    instant = resolve_wall(payload["wall_start"], payload["zone_name"], int(payload["offset_minutes"]))
    if instant.astimezone(timezone.utc) < datetime.now(timezone.utc) + LEAD:
        raise CommandError(409, "lead_time", "That time is inside the lead-time window.", False)
    body = {
        "capability_hash": _hash(payload["capability"]),
        "mode": payload.get("mode") or "individual",
        "wall_start": payload["wall_start"],
        "zone_name": payload["zone_name"],
        "offset_minutes": int(payload["offset_minutes"]),
        "starts_at": instant.isoformat(),
        "ends_at": (instant + DURATION).isoformat(),
        "guest_count": int(payload.get("guest_count") or 1),
        "host_resource_id": payload.get("host_resource_id") or "",
        "space_resource_id": payload.get("space_resource_id") or "",
    }
    fingerprint = hashlib.sha256(repr(sorted(body.items())).encode()).hexdigest()
    try:
        with runtime_transaction(settings, None, None, uuid4()) as connection:
            row = connection.execute(
                text("SELECT perchpoint.commit_showing(CAST(:intake AS jsonb), CAST(:key AS text), CAST(:fingerprint AS text))"),
                {"intake": json.dumps(body), "key": idempotency_key, "fingerprint": fingerprint},
            ).scalar_one()
    except IntegrityError as exc:
        raise CommandError(409, "slot_unavailable", "That time is no longer available.", False) from exc
    except OperationalError as exc:
        if getattr(exc.orig, "sqlstate", "") != "40P01":
            raise
        raise CommandError(409, "slot_unavailable", "That time is no longer available.", False) from exc
    if not row["accepted"]:
        status = 409 if row["code"] == "conflict" else 400
        raise CommandError(status, row["code"], "The showing request could not be accepted.", False)
    return {"accepted": True, "reference": row["reference"], "replayed": row["replayed"], "wall_start": payload["wall_start"], "zone_name": payload["zone_name"], "duration_minutes": 30}


def create_resource(settings: Settings, actor, organization: str, kind: str, label: str, capacity: int, parent_id: str | None) -> dict:
    resource = str(uuid4())
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        connection.execute(
            text(
                "INSERT INTO showing_resources (organization_id, id, kind, parent_id, label, capacity) "
                "VALUES (CAST(:org AS uuid), CAST(:id AS uuid), :kind, CAST(:parent AS uuid), :label, :capacity)"
            ),
            {"org": organization, "id": resource, "kind": kind, "parent": parent_id, "label": label, "capacity": capacity},
        )
    return {"id": resource}


def cancel(settings: Settings, actor, organization: str, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text("SELECT id FROM showings WHERE public_reference = :reference"),
            {"reference": reference},
        ).first()
        if row is None:
            raise CommandError(404, "not_found", "The appointment was not found.", False)
        connection.execute(text("UPDATE showings SET business_state = 'cancelled', version = version + 1 WHERE id = :id"), {"id": row.id})
        connection.execute(text("DELETE FROM showing_occupancy WHERE showing_id = :id"), {"id": row.id})
        connection.execute(
            text("INSERT INTO showing_impacts (organization_id, id, showing_id, reason, state) VALUES (CAST(:org AS uuid), gen_random_uuid(), :id, 'cancelled', 'open')"),
            {"org": organization, "id": row.id},
        )
    return {"state": "cancelled"}


def complete(settings: Settings, actor, organization: str, reference: str) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(text("SELECT id, inquiry_id FROM showings WHERE public_reference = :reference"), {"reference": reference}).first()
        if row is None:
            raise CommandError(404, "not_found", "The appointment was not found.", False)
        connection.execute(text("UPDATE showings SET business_state = 'completed', version = version + 1 WHERE id = :id"), {"id": row.id})
        connection.execute(text("UPDATE inquiry_actions SET is_primary = false WHERE inquiry_id = :inquiry AND is_primary AND status = 'open'"), {"inquiry": row.inquiry_id})
        connection.execute(
            text(
                "INSERT INTO inquiry_actions (organization_id, id, inquiry_id, kind, status, is_primary, due_at) "
                "VALUES (CAST(:org AS uuid), gen_random_uuid(), :inquiry, 'showing_follow_up', 'open', true, now() + interval '1 day')"
            ),
            {"org": organization, "inquiry": row.inquiry_id},
        )
    return {"state": "completed", "next_action": "showing_follow_up"}


def start_connection(settings: Settings, actor, organization: str) -> dict:
    connection_id = str(uuid4())
    state = secrets.token_urlsafe(24)
    verifier = secrets.token_urlsafe(48)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        connection.execute(
            text(
                "INSERT INTO calendar_connections (organization_id, id, account_id, provider_code, token_envelope, state) "
                "VALUES (CAST(:org AS uuid), CAST(:id AS uuid), CAST(:account AS uuid), 'fake', :state, 'pending')"
            ),
            {"org": organization, "id": connection_id, "account": actor, "state": state},
        )
    return {"connection_id": connection_id, "state": state, "verifier": verifier, "challenge": challenge}


def finish_connection(settings: Settings, actor, organization: str, connection_id: str, code: str, state: str, verifier: str, challenge: str) -> dict:
    digest = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).decode().rstrip("=")
    if code != "fake-auth-code" or digest != challenge:
        raise CommandError(400, "rejected", "The calendar connection could not be accepted.", False)
    envelope = _seal(settings, "fake-refresh-token")
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text("SELECT token_envelope, state FROM calendar_connections WHERE id = :id"),
            {"id": connection_id},
        ).first()
        if row is None or row.state != "pending" or row.token_envelope != state:
            raise CommandError(400, "rejected", "The calendar connection could not be accepted.", False)
        connection.execute(
            text("UPDATE calendar_connections SET token_envelope = :envelope, state = 'active' WHERE id = :id"),
            {"envelope": envelope, "id": connection_id},
        )
    return {"connection_id": connection_id, "state": "active"}


def refresh_connection(settings: Settings, actor, organization: str, connection_id: str, expected_version: int) -> dict:
    with runtime_transaction(settings, actor, _org(organization), uuid4()) as connection:
        _require(connection, "inquiry.manage")
        row = connection.execute(
            text("SELECT token_version, token_envelope, state FROM calendar_connections WHERE id = :id FOR UPDATE"),
            {"id": connection_id},
        ).first()
        if row is None or row.state != "active":
            raise CommandError(404, "not_found", "The calendar connection was not found.", False)
        if row.token_version != expected_version:
            raise CommandError(409, "stale_token", "The token version is stale.", False)
        _open(settings, row.token_envelope)
        connection.execute(
            text("UPDATE calendar_connections SET token_version = token_version + 1, token_envelope = :envelope WHERE id = :id"),
            {"envelope": _seal(settings, f"fake-refresh-token-{expected_version + 1}"), "id": connection_id},
        )
    return {"token_version": expected_version + 1}


def apply_callback(settings: Settings, body: bytes, signature: str) -> dict:
    expected = hmac.new(settings.webhook_secret.encode(), body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature or ""):
        raise CommandError(400, "rejected", "The callback could not be accepted.", False)
    import json
    payload = json.loads(body)
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(
            text("SELECT perchpoint.apply_calendar_callback(CAST(:reference AS text), CAST(:event_id AS text), CAST(:change AS text))"),
            {"reference": payload["reference"], "event_id": payload["event_id"], "change": payload["change"]},
        ).scalar_one()
    if not row["accepted"]:
        raise CommandError(400, "rejected", "The callback could not be accepted.", False)
    return row


def _seal(settings: Settings, secret: str) -> str:
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest())
    return Fernet(key).encrypt(secret.encode()).decode()


def _open(settings: Settings, envelope: str) -> str:
    from cryptography.fernet import Fernet
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.jwt_secret.encode()).digest())
    return Fernet(key).decrypt(envelope.encode()).decode()

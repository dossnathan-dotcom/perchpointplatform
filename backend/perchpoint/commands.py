"""Material commands. Domain, redacted audit, and outbox commit together."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from uuid import UUID, uuid4

from foundation.reference import allowed_space_transition

from sqlalchemy import text
from sqlalchemy.engine import Connection

from .db import runtime_transaction
from .settings import Settings


class CommandError(Exception):
    def __init__(self, status: int, code: str, message: str, retryable: bool = False):
        self.status = status
        self.code = code
        self.message = message
        self.retryable = retryable


def fingerprint(payload: dict) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def create_property(settings: Settings, actor: UUID, organization: UUID, body: dict, key: str, correlation: UUID) -> dict:
    payload = {"name": body["name"], "property_type": body["property_type"]}
    return _command(settings, actor, organization, key, payload, correlation, "property.created", lambda conn, fp: _insert_property(conn, organization, actor, payload, correlation))


def submit_public_inquiry(settings: Settings, body: dict, correlation: UUID) -> dict:
    payload = {field: body[field] for field in ("listing_id", "name", "email", "intent", "message")}
    fp = fingerprint(payload)
    with runtime_transaction(settings, None, None, correlation) as connection:
        row = connection.execute(
            text(
                """
                SELECT inquiry_id, status, correlation_id, conflict
                FROM perchpoint.submit_public_inquiry(:listing_id, :name, :email, :intent, :message, :key, :fp, :correlation)
                """
            ),
            {**payload, "key": body["idempotency_key"], "fp": fp, "correlation": correlation},
        ).mappings().first()
        if row["conflict"]:
            raise CommandError(409, "idempotency_conflict", "This key was already used for a different request")
        return {"inquiry_id": str(row["inquiry_id"]), "status": row["status"], "correlation_id": str(row["correlation_id"]), "synthetic": True}


def create_building(settings: Settings, actor: UUID, organization: UUID, body: dict, key: str, correlation: UUID) -> dict:
    payload = {"property_id": body["property_id"], "name": body["name"], "allowed_uses": body["allowed_uses"]}
    return _command(settings, actor, organization, key, payload, correlation, "building.created", lambda conn, fp: _insert_building(conn, organization, actor, payload, correlation))


def create_space(settings: Settings, actor: UUID, organization: UUID, body: dict, key: str, correlation: UUID) -> dict:
    payload = {"property_id": body["property_id"], "building_id": body["building_id"], "label": body["label"], "use": body["use"], "square_feet": body["square_feet"]}
    return _command(settings, actor, organization, key, payload, correlation, "space.created", lambda conn, fp: _insert_space(conn, organization, actor, payload, correlation))


def update_property(settings: Settings, actor: UUID, organization: UUID, property_id: UUID, body: dict, key: str, correlation: UUID) -> dict:
    payload = {"property_id": str(property_id), "name": body["name"], "expected_version": body["expected_version"]}
    return _command(settings, actor, organization, key, payload, correlation, "property.updated", lambda conn, fp: _rename_property(conn, organization, actor, property_id, body, correlation))


def set_space_dimension(settings: Settings, actor: UUID, organization: UUID, space_id: UUID, body: dict, key: str, correlation: UUID) -> dict:
    payload = {"space_id": str(space_id), "dimension": body["dimension"], "value": body["value"], "expected_version": body["expected_version"]}
    return _command(settings, actor, organization, key, payload, correlation, "space.transitioned", lambda conn, fp: _transition_space(conn, organization, actor, space_id, body, correlation))


def claim_and_deliver(settings: Settings, worker_name: str) -> dict:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(text("SELECT * FROM perchpoint.claim_outbox(:worker)"), {"worker": worker_name}).mappings().first()
        if not row:
            return {"claimed": False}
        claimed = dict(row)
    if claimed["attempts"] >= 5:
        return {"claimed": True, "status": "dead_letter", "id": str(claimed["id"])}
    payload = claimed["payload"] if isinstance(claimed["payload"], dict) else json.loads(claimed["payload"])
    delivered = not (payload.get("fail_once") and claimed["attempts"] == 1)
    status = connection_finish(settings, claimed["id"], delivered)
    return {"claimed": True, "status": status, "id": str(claimed["id"]), "synthetic": True, "exactly_once": False}


def connection_finish(settings: Settings, outbox_id: UUID, delivered: bool) -> str:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        return connection.execute(text("SELECT perchpoint.finish_outbox(:id, :delivered)"), {"id": outbox_id, "delivered": delivered}).scalar()


def triage_inquiry(settings: Settings, actor: UUID, organization: UUID, inquiry_id: UUID, body: dict, key: str, correlation: UUID) -> dict:
    payload = {"inquiry_id": str(inquiry_id), "decision": body["decision"], "expected_version": body["expected_version"]}
    return _command(settings, actor, organization, key, payload, correlation, "inquiry.triaged", lambda conn, fp: _triage(conn, organization, actor, inquiry_id, body, correlation))


def _insert_property(connection: Connection, organization: UUID, actor: UUID, payload: dict, correlation: UUID) -> dict:
    property_id = uuid4()
    connection.execute(
        text("INSERT INTO properties (organization_id, id, name, property_type) VALUES (:org, :id, :name, :kind)"),
        {"org": organization, "id": property_id, "name": payload["name"], "kind": payload["property_type"]},
    )
    result = {"id": str(property_id), "version": 1}
    _audit_outbox(connection, organization, actor, "property.created", property_id, correlation, "property.created.v1", result)
    return result


def _insert_building(connection: Connection, organization: UUID, actor: UUID, payload: dict, correlation: UUID) -> dict:
    building_id = uuid4()
    connection.execute(
        text("INSERT INTO buildings (organization_id, id, property_id, name, allowed_uses) VALUES (:org, :id, :property, :name, :uses)"),
        {"org": organization, "id": building_id, "property": payload["property_id"], "name": payload["name"], "uses": payload["allowed_uses"]},
    )
    result = {"id": str(building_id), "property_id": payload["property_id"]}
    _audit_outbox(connection, organization, actor, "building.created", building_id, correlation, "building.created.v1", result)
    return result


def _insert_space(connection: Connection, organization: UUID, actor: UUID, payload: dict, correlation: UUID) -> dict:
    space_id = uuid4()
    connection.execute(
        text(
            """
            INSERT INTO spaces (organization_id, id, property_id, building_id, label, use, square_feet)
            VALUES (:org, :id, :property, :building, :label, :use, :area)
            """
        ),
        {"org": organization, "id": space_id, "property": payload["property_id"], "building": payload["building_id"], "label": payload["label"], "use": payload["use"], "area": payload["square_feet"]},
    )
    connection.execute(
        text(
            """
            INSERT INTO space_states (
              organization_id, id, space_id, condition, occupancy, availability, publication,
              maintenance_restriction, legal_restriction, version, current
            ) VALUES (:org, :id, :space, 'rent_ready', 'vacant', 'withheld', 'unpublished', 'none', 'none', 1, true)
            """
        ),
        {"org": organization, "id": uuid4(), "space": space_id},
    )
    result = {"id": str(space_id), "use": payload["use"], "version": 1}
    _audit_outbox(connection, organization, actor, "space.created", space_id, correlation, "space.created.v1", result)
    return result


def _rename_property(connection: Connection, organization: UUID, actor: UUID, property_id: UUID, body: dict, correlation: UUID) -> dict:
    row = connection.execute(
        text("UPDATE properties SET name = :name, version = version + 1 WHERE organization_id = :org AND id = :id AND version = :expected RETURNING version"),
        {"name": body["name"], "org": organization, "id": property_id, "expected": body["expected_version"]},
    ).first()
    if not row:
        current = connection.execute(text("SELECT version FROM properties WHERE organization_id = :org AND id = :id"), {"org": organization, "id": property_id}).first()
        if not current:
            raise CommandError(404, "not_found", "Property was not found")
        raise CommandError(409, "stale_version", "The property changed. Reload and try again.", retryable=True)
    result = {"id": str(property_id), "version": row.version, "name": body["name"]}
    _audit_outbox(connection, organization, actor, "property.updated", property_id, correlation, "property.updated.v1", result)
    return result


def _transition_space(connection: Connection, organization: UUID, actor: UUID, space_id: UUID, body: dict, correlation: UUID) -> dict:
    dimension = body["dimension"]
    if dimension not in {"availability", "publication", "condition", "occupancy", "maintenance_restriction", "legal_restriction"}:
        raise CommandError(422, "invalid_dimension", "That space dimension cannot be changed here")
    current = connection.execute(
        text(f"SELECT id, {dimension} AS current_value, version, availability, legal_restriction FROM space_states WHERE organization_id = :org AND space_id = :space AND current FOR UPDATE"),
        {"org": organization, "space": space_id},
    ).mappings().first()
    if not current:
        raise CommandError(404, "not_found", "Space state was not found")
    if current["version"] != body["expected_version"]:
        raise CommandError(409, "stale_version", "The space changed. Reload and try again.", retryable=True)
    if not allowed_space_transition(dimension, current["current_value"], body["value"]):
        raise CommandError(422, "invalid_transition", "That space transition is not allowed")
    connection.execute(
        text(f"UPDATE space_states SET {dimension} = :value, version = version + 1 WHERE id = :id"),
        {"value": body["value"], "id": current["id"]},
    )
    result = {"id": str(space_id), "dimension": dimension, "value": body["value"], "version": current["version"] + 1}
    _audit_outbox(connection, organization, actor, "space.transitioned", space_id, correlation, "space.transitioned.v1", result)
    return result


def _triage(connection: Connection, organization: UUID, actor: UUID, inquiry_id: UUID, body: dict, correlation: UUID) -> dict:
    current = connection.execute(
        text("SELECT version, status FROM inquiries WHERE organization_id = :org AND id = :id FOR UPDATE"),
        {"org": organization, "id": inquiry_id},
    ).mappings().first()
    if not current:
        raise CommandError(404, "not_found", "Inquiry was not found")
    if current["version"] != body["expected_version"]:
        raise CommandError(409, "stale_version", "The inquiry changed. Reload and try again.", retryable=True)
    connection.execute(
        text("UPDATE inquiries SET status = :status, assigned_account_id = :actor, version = version + 1 WHERE id = :id"),
        {"status": body["decision"], "actor": actor, "id": inquiry_id},
    )
    connection.execute(
        text(
            """
            INSERT INTO activity (organization_id, id, resource_type, resource_id, summary, occurred_at, actor_id)
            VALUES (:org, :id, 'inquiry', :resource, :summary, now(), :actor)
            """
        ),
        {"org": organization, "id": uuid4(), "resource": inquiry_id, "summary": f"Triage {body['decision']}", "actor": actor},
    )
    result = {"id": str(inquiry_id), "status": body["decision"], "version": current["version"] + 1}
    _audit_outbox(connection, organization, actor, "inquiry.triaged", inquiry_id, correlation, "inquiry.triaged.v1", result)
    return result


def accept_inbox(settings: Settings, raw_body: bytes, signature: str, organization: UUID) -> dict:
    expected = hmac.new(settings.webhook_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise CommandError(401, "invalid_signature", "Webhook signature was rejected")
    payload = json.loads(raw_body)
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        disposition = connection.execute(
            text(
                """
                SELECT perchpoint.accept_inbox(:org, :provider, :account, :environment, :event_id, CAST(:payload AS jsonb), :version)
                """
            ),
            {
                "org": organization,
                "provider": payload["provider"],
                "account": payload["account_name"],
                "environment": payload["environment"],
                "event_id": payload["provider_event_id"],
                "payload": json.dumps(payload),
                "version": payload.get("aggregate_version"),
            },
        ).scalar()
    return {"disposition": disposition, "synthetic": True}


def _command(settings, actor, organization, key, payload, correlation, action, writer) -> dict:
    fp = fingerprint(payload)
    with runtime_transaction(settings, actor, organization, correlation) as connection:
        connection.execute(text("SELECT pg_advisory_xact_lock(hashtextextended(:key, 0))"), {"key": f"{organization}:{key}"})
        existing = connection.execute(
            text("SELECT fingerprint, result FROM idempotency_keys WHERE organization_id = :org AND idempotency_key = :key"),
            {"org": organization, "key": key},
        ).mappings().first()
        if existing:
            if existing["fingerprint"] != fp:
                raise CommandError(409, "idempotency_conflict", "This key was already used for a different request")
            return existing["result"]
        result = writer(connection, fp)
        connection.execute(
            text(
                """
                INSERT INTO idempotency_keys (organization_id, idempotency_key, fingerprint, result, created_at)
                VALUES (:org, :key, :fp, CAST(:result AS jsonb), now())
                """
            ),
            {"org": organization, "key": key, "fp": fp, "result": json.dumps(result)},
        )
        return result


def _audit_outbox(connection, organization, actor, action, resource, correlation, event_type, result) -> None:
    previous = connection.execute(
        text("SELECT event_hash FROM audit_events WHERE organization_id = :org ORDER BY occurred_at DESC LIMIT 1"),
        {"org": organization},
    ).scalar()
    event_hash = hashlib.sha256(f"{previous}|{action}|{resource}|{correlation}".encode()).hexdigest()
    connection.execute(
        text(
            """
            INSERT INTO audit_events (
              organization_id, id, actor_id, action, resource_type, resource_id, occurred_at,
              correlation_id, result, previous_event_hash, event_hash
            ) VALUES (:org, :id, :actor, :action, 'record', :resource, now(), :correlation, 'allowed', :previous, :hash)
            """
        ),
        {"org": organization, "id": uuid4(), "actor": actor, "action": action, "resource": resource, "correlation": correlation, "previous": previous, "hash": event_hash},
    )
    if os.environ.get("PHASE2_INJECT_BEFORE_OUTBOX") == "1":
        raise CommandError(500, "injected_failure", "Injected failure before the outbox write")
    connection.execute(
        text(
            """
            INSERT INTO activity (organization_id, id, resource_type, resource_id, summary, occurred_at, actor_id)
            VALUES (:org, :id, 'record', :resource, :summary, now(), :actor)
            """
        ),
        {"org": organization, "id": uuid4(), "resource": resource, "summary": action, "actor": actor},
    )
    connection.execute(
        text(
            """
            INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, available_at)
            VALUES (:org, :id, :event_type, :aggregate, CAST(:payload AS jsonb), 'pending', now())
            """
        ),
        {"org": organization, "id": uuid4(), "event_type": event_type, "aggregate": resource, "payload": json.dumps({"synthetic": True, "result": result, "fail_once": bool(result.get("fail_once"))})},
    )

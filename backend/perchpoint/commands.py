"""Material commands. Domain, redacted audit, and outbox commit together."""
from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

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


def claim_and_deliver(settings: Settings, worker_name: str) -> dict:
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        row = connection.execute(text("SELECT * FROM perchpoint.claim_outbox(:worker)"), {"worker": worker_name}).mappings().first()
        if not row:
            return {"claimed": False}
        claimed_id = row["id"]
        if row["attempts"] >= 5:
            return {"claimed": True, "status": "dead_letter", "id": str(claimed_id)}
    status = connection_finish(settings, claimed_id, True)
    return {"claimed": True, "status": status, "id": str(claimed_id)}


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


def _command(settings, actor, organization, key, payload, correlation, action, writer) -> dict:
    fp = fingerprint(payload)
    with runtime_transaction(settings, actor, organization, correlation) as connection:
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
    connection.execute(
        text(
            """
            INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, available_at)
            VALUES (:org, :id, :event_type, :aggregate, CAST(:payload AS jsonb), 'pending', now())
            """
        ),
        {"org": organization, "id": uuid4(), "event_type": event_type, "aggregate": resource, "payload": json.dumps({"synthetic": True, "result": result})},
    )

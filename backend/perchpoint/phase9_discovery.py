"""Phase 9 discovery projections for HawkVision-owned surfaces.

Search reads immutable Phase 8 snapshots. External syndication stays disabled.
This module does not create inquiries, showings, applications, or leases.
"""
from __future__ import annotations

import hashlib
import json
import re
from uuid import uuid4

from sqlalchemy import text

from .commands import CommandError, _audit_outbox, _command

OWNED_TARGETS = ("discovery_index", "public_page", "sitemap", "link_preview", "health")
FORBIDDEN = {"organization_id", "resident", "access_code", "internal_note", "cost_minor", "email", "phone"}
PROHIBITED_CHANNELS = ("zillow", "facebook", "mls", "craigslist", "syndication")
PII = re.compile(r"@", re.I)
EVENTS = {"search", "impression", "detail", "cta"}


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized")


def _role(connection) -> str:
    return connection.execute(text("SELECT perchpoint.role_for_account(perchpoint.current_actor())")).scalar() or ""


def _public_payload(snapshot: dict, use_code: str) -> dict:
    source = snapshot if isinstance(snapshot, dict) else json.loads(snapshot)
    payload = {
        "property_name": source.get("property_name") or "",
        "label": source.get("label") or "",
        "municipality": source.get("municipality") or "",
        "state": source.get("state") or "",
        "availability": "available",
        "amount_minor": int(source.get("amount_minor") or 0),
        "currency": source.get("currency") or "USD",
        "period": "monthly",
        "estimate_minor": int(source.get("estimate_minor") or source.get("amount_minor") or 0),
        "estimate_disclaimer": source.get("estimate_disclaimer") or "EXAMPLE ONLY. This is a listing estimate, not a resident ledger balance.",
        "description": source.get("description") or "EXAMPLE ONLY. Synthetic listing facts.",
        "alt_text": source.get("alt_text") or "",
        "use_code": use_code,
        "schema_version": 1,
        "synthetic": True,
    }
    if FORBIDDEN & set(payload):
        raise CommandError(422, "projection_rejected", "The discovery projection contains a prohibited field")
    return payload


def project_listing(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, fingerprint):
        _require(connection, "property.manage")
        if any(token in str(body.get("target", "")).lower() for token in PROHIBITED_CHANNELS):
            raise CommandError(422, "channel_disabled", "External syndication is disabled by policy")
        snapshot = connection.execute(
            text(
                """
                SELECT snapshot.id, snapshot.listing_id, snapshot.public_slug, snapshot.payload, snapshot.content_hash,
                       snapshot.superseded_at, listing.publication, listing.version AS listing_version, space.use
                FROM listing_snapshots snapshot
                JOIN listings listing ON listing.organization_id = snapshot.organization_id AND listing.id = snapshot.listing_id
                JOIN spaces space ON space.organization_id = listing.organization_id AND space.id = listing.space_id
                WHERE snapshot.organization_id = :org AND snapshot.id = :id
                """
            ),
            {"org": organization, "id": body["snapshot_id"]},
        ).mappings().first()
        if not snapshot or snapshot["superseded_at"] is not None or snapshot["publication"] != "published":
            raise CommandError(422, "not_eligible", "Only a current published snapshot can enter discovery")
        payload = _public_payload(snapshot["payload"], snapshot["use"] or "residential")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        current = connection.execute(
            text(
                """
                SELECT id, version, content_hash FROM discovery_projections
                WHERE organization_id = :org AND listing_id = :listing AND current
                """
            ),
            {"org": organization, "listing": snapshot["listing_id"]},
        ).mappings().first()
        version = 1 if not current else int(current["version"]) + 1
        if current and current["content_hash"] == digest:
            result = {"id": str(current["id"]), "version": int(current["version"]), "replayed": True, "synthetic": True}
            return result
        if current:
            connection.execute(
                text("UPDATE discovery_projections SET current = false WHERE organization_id = :org AND id = :id"),
                {"org": organization, "id": current["id"]},
            )
        projection_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO discovery_projections (
                  organization_id, id, listing_id, snapshot_id, public_slug, schema_version, policy_version,
                  content_hash, eligibility, payload, search_text, city, use_code, amount_minor, currency, period,
                  bedrooms, sort_rank, version
                ) VALUES (
                  :org, :id, :listing, :snapshot, :slug, 1, 1, :digest, 'eligible', CAST(:payload AS jsonb),
                  :search, :city, :use, :amount, :currency, 'monthly', :beds, :rank, :version
                )
                """
            ),
            {
                "org": organization,
                "id": projection_id,
                "listing": snapshot["listing_id"],
                "snapshot": snapshot["id"],
                "slug": snapshot["public_slug"],
                "digest": digest,
                "payload": encoded,
                "search": " ".join([payload["property_name"], payload["label"], payload["municipality"], payload["description"]]),
                "city": payload["municipality"],
                "use": payload["use_code"],
                "amount": payload["amount_minor"],
                "currency": payload["currency"],
                "beds": body.get("bedrooms"),
                "rank": 100,
                "version": version,
            },
        )
        for target in OWNED_TARGETS:
            connection.execute(
                text(
                    """
                    INSERT INTO distribution_operations (
                      organization_id, id, projection_id, target_code, operation, idempotency_key, fingerprint,
                      projection_version, priority, state, observed_hash
                    ) VALUES (
                      :org, :id, :projection, :target, 'publish', :key, :fingerprint, :version, 10, 'done', :digest
                    )
                    """
                ),
                {
                    "org": organization,
                    "id": uuid4(),
                    "projection": projection_id,
                    "target": target,
                    "key": f"{key}:{target}",
                    "fingerprint": fingerprint,
                    "version": version,
                    "digest": digest,
                },
            )
        result = {"id": str(projection_id), "public_slug": snapshot["public_slug"], "version": version, "content_hash": digest, "synthetic": True}
        _audit_outbox(connection, organization, actor, "discovery.projected", projection_id, correlation, "discovery.projected.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "discovery.projected", write)


def withdraw_listing(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, fingerprint):
        _require(connection, "property.manage")
        row = connection.execute(
            text(
                """
                UPDATE discovery_projections
                SET eligibility = 'withdrawn', version = version + 1
                WHERE organization_id = :org AND public_slug = :slug AND current AND eligibility = 'eligible'
                RETURNING id, version
                """
            ),
            {"org": organization, "slug": body["public_slug"]},
        ).mappings().first()
        if not row:
            raise CommandError(404, "not_found", "Eligible discovery projection was not found")
        connection.execute(
            text(
                """
                INSERT INTO distribution_operations (
                  organization_id, id, projection_id, target_code, operation, idempotency_key, fingerprint,
                  projection_version, priority, state
                ) VALUES (
                  :org, :id, :projection, 'discovery_index', 'withdraw', :key, :fingerprint, :version, 1, 'done'
                )
                """
            ),
            {
                "org": organization,
                "id": uuid4(),
                "projection": row["id"],
                "key": key,
                "fingerprint": fingerprint,
                "version": row["version"],
            },
        )
        result = {"id": str(row["id"]), "eligibility": "withdrawn", "version": int(row["version"]), "synthetic": True}
        _audit_outbox(connection, organization, actor, "discovery.withdrawn", row["id"], correlation, "discovery.withdrawn.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "discovery.withdrawn", write)


def approve_ranking(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "approval.owner")
        if _role(connection) != "owner":
            raise CommandError(403, "owner_reserved", "Ranking policy is reserved for the owner")
        policy_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO ranking_policies (organization_id, id, version, reason, actor_id, effective_on)
                VALUES (:org, :id, :version, :reason, :actor, :effective)
                """
            ),
            {
                "org": organization,
                "id": policy_id,
                "version": int(body["version"]),
                "reason": body["reason"],
                "actor": actor,
                "effective": body["effective_on"],
            },
        )
        result = {"id": str(policy_id), "version": int(body["version"]), "synthetic": True}
        _audit_outbox(connection, organization, actor, "discovery.ranking_approved", policy_id, correlation, "discovery.ranking_approved.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "discovery.ranking_approved", write)


def reconcile(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        stale = connection.execute(
            text(
                """
                SELECT projection.id
                FROM discovery_projections projection
                JOIN listing_snapshots snapshot ON snapshot.organization_id = projection.organization_id
                  AND snapshot.id = projection.snapshot_id
                WHERE projection.organization_id = :org AND projection.current AND projection.eligibility = 'eligible'
                  AND snapshot.superseded_at IS NOT NULL
                """
            ),
            {"org": organization},
        ).all()
        repaired = 0
        for row in stale:
            connection.execute(
                text("UPDATE discovery_projections SET eligibility = 'withdrawn', version = version + 1 WHERE organization_id = :org AND id = :id"),
                {"org": organization, "id": row.id},
            )
            repaired += 1
        expected = connection.execute(
            text("SELECT count(*) FROM discovery_projections WHERE organization_id = :org AND current AND eligibility = 'eligible'"),
            {"org": organization},
        ).scalar()
        run_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO reconciliation_runs (organization_id, id, expected_count, observed_count, repaired_count, status)
                VALUES (:org, :id, :expected, :observed, :repaired, 'completed')
                """
            ),
            {"org": organization, "id": run_id, "expected": expected, "observed": expected, "repaired": repaired},
        )
        result = {"id": str(run_id), "expected_count": int(expected or 0), "repaired_count": repaired, "status": "completed", "synthetic": True}
        _audit_outbox(connection, organization, actor, "discovery.reconciled", run_id, correlation, "discovery.reconciled.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "discovery.reconciled", write)


def search_public(settings, criteria: dict) -> dict:
    from .db import runtime_transaction

    safe = {key: str(value) for key, value in criteria.items() if value not in (None, "")}
    for token in PROHIBITED_CHANNELS:
        if token in json.dumps(safe).lower():
            raise CommandError(400, "rejected", "That search is not available")
    query = safe.get("query", "")
    if len(query) > 80:
        raise CommandError(400, "rejected", "The search is too long")
    safe["query"] = re.sub(r"[%_]", "", query)
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        payload = connection.execute(text("SELECT perchpoint.search_discovery(CAST(:criteria AS jsonb))"), {"criteria": json.dumps(safe)}).scalar()
    if isinstance(payload, str):
        payload = json.loads(payload)
    return payload or {"total": 0, "records": [], "facets": {"residential": 0, "commercial": 0}}


def public_listing(settings, slug: str):
    from .db import runtime_transaction

    with runtime_transaction(settings, None, None, uuid4()) as connection:
        payload = connection.execute(text("SELECT perchpoint.published_discovery_listing(:slug)"), {"slug": slug}).scalar()
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def sitemap(settings) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, None, None, uuid4()) as connection:
        rows = connection.execute(text("SELECT perchpoint.discovery_sitemap()")).scalar() or []
    if isinstance(rows, str):
        rows = json.loads(rows)
    urls = "".join(f"<url><loc>{item['loc']}</loc></url>" for item in rows)
    return {"xml": f"<urlset>{urls}</urlset>", "count": len(rows), "synthetic": True}


def record_event(settings, body: dict, *, gpc: bool) -> dict:
    from .db import runtime_transaction

    if body.get("event_name") not in EVENTS:
        raise CommandError(422, "rejected", "That event is not in the discovery taxonomy")
    blob = json.dumps(body)
    if PII.search(blob) or any(token in body for token in ("email", "phone", "name", "access_code")):
        raise CommandError(422, "rejected", "Discovery events cannot carry personal data")
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        payload = connection.execute(
            text(
                """
                SELECT perchpoint.record_discovery_event(:slug, :name, :session, :source, :medium, :campaign, :key, :gpc)
                """
            ),
            {
                "slug": body.get("listing_slug") or "",
                "name": body["event_name"],
                "session": body.get("session_ref") or "session",
                "source": body.get("source") or "",
                "medium": body.get("medium") or "",
                "campaign": body.get("campaign") or "",
                "key": body["idempotency_key"],
                "gpc": gpc,
            },
        ).scalar()
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not payload or payload.get("found") is False:
        raise CommandError(404, "not_found", "That listing is not in discovery")
    payload["synthetic"] = True
    payload.pop("found", None)
    return payload


def health(settings, actor, organization) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, "property.read")
        eligible = connection.execute(
            text("SELECT count(*) FROM discovery_projections WHERE current AND eligibility = 'eligible'")
        ).scalar()
        withdrawn = connection.execute(
            text("SELECT count(*) FROM discovery_projections WHERE current AND eligibility = 'withdrawn'")
        ).scalar()
    return {"eligible": int(eligible or 0), "withdrawn": int(withdrawn or 0), "channels": list(OWNED_TARGETS), "external_syndication": "disabled", "synthetic": True}

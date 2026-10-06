"""Phase 8 property truth: pricing, holds, media review, and publication snapshots.

Synthetic pricing bands are examples. They are not production policy and do not
grant Faruk's stakeholder or legal acceptance.
"""
from __future__ import annotations

import hashlib
import json
from uuid import UUID, uuid4

from sqlalchemy import text

from .commands import CommandError, _audit_outbox, _command

MATERIAL_ABSOLUTE_MINOR = 15000
MATERIAL_PERCENT = 10
PROHIBITED = ("no children", "christian only", "perfect for singles")
FORBIDDEN_PUBLIC = {"organization_id", "resident", "cost_minor", "access_code", "internal_note"}
READINESS_TRANSITIONS = {
    "not_assessed": {"occupied_not_turning", "notice_pending", "turn_required", "blocked", "ready"},
    "occupied_not_turning": {"notice_pending", "not_assessed"},
    "notice_pending": {"turn_required", "occupied_not_turning"},
    "turn_required": {"work_in_progress", "blocked"},
    "work_in_progress": {"inspection_required", "blocked"},
    "inspection_required": {"ready", "work_in_progress", "blocked"},
    "ready": {"turn_required", "blocked"},
    "blocked": {"not_assessed", "turn_required"},
}
AVAILABILITY_TRANSITIONS = {
    "not_offered": {"coming_soon", "off_market"},
    "coming_soon": {"available", "off_market", "not_offered"},
    "available": {"temporary_hold", "application_pending", "off_market", "leased"},
    "temporary_hold": {"available", "off_market"},
    "application_pending": {"lease_pending", "available", "off_market"},
    "lease_pending": {"leased", "available"},
    "leased": {"off_market", "not_offered"},
    "off_market": {"not_offered", "coming_soon"},
}


def _require(connection, capability: str) -> None:
    allowed = connection.execute(
        text("SELECT perchpoint.has_capability(:capability)"),
        {"capability": capability},
    ).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized")


def _visible_space(connection, space_id) -> None:
    row = connection.execute(text("SELECT id FROM spaces WHERE id = :space"), {"space": space_id}).first()
    if not row:
        raise CommandError(404, "not_found", "Space was not found")


def _material(previous: int, proposed: int) -> bool:
    delta = abs(proposed - previous)
    if delta >= MATERIAL_ABSOLUTE_MINOR:
        return True
    return previous > 0 and delta * 100 >= previous * MATERIAL_PERCENT


def _role(connection, actor: UUID) -> str | None:
    return connection.execute(text("SELECT perchpoint.role_for_account(:actor)"), {"actor": actor}).scalar()


def inventory(settings, actor: UUID, organization: UUID) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        rows = connection.execute(
            text(
                """
                SELECT property.id AS property_id, property.name, property.lifecycle, property.version,
                       listing.id AS listing_id, listing.public_slug, listing.publication, listing.version AS listing_version,
                       space.id AS space_id, space.label, space.use
                FROM properties property
                JOIN spaces space ON space.organization_id = property.organization_id AND space.property_id = property.id
                LEFT JOIN listings listing ON listing.organization_id = space.organization_id AND listing.space_id = space.id
                ORDER BY property.name, space.label
                """
            )
        ).mappings().all()
    return {"records": [dict(row) for row in rows], "synthetic": True}


def set_readiness(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        _visible_space(connection, body["space_id"])
        current = connection.execute(
            text(
                """
                SELECT id, readiness FROM space_readiness
                WHERE organization_id = :org AND space_id = :space AND current
                """
            ),
            {"org": organization, "space": body["space_id"]},
        ).mappings().first()
        previous = current["readiness"] if current else "not_assessed"
        nxt = body["readiness"]
        if current and nxt not in READINESS_TRANSITIONS[previous]:
            raise CommandError(422, "invalid_transition", "That readiness transition is not allowed")
        if current:
            connection.execute(text("UPDATE space_readiness SET current = false WHERE id = :id"), {"id": current["id"]})
        record_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO space_readiness (organization_id, id, space_id, readiness, reason, actor_id)
                VALUES (:org, :id, :space, :readiness, :reason, :actor)
                """
            ),
            {"org": organization, "id": record_id, "space": body["space_id"], "readiness": nxt, "reason": body["reason"], "actor": actor},
        )
        result = {"id": str(record_id), "readiness": nxt, "previous": previous, "synthetic": True}
        _audit_outbox(connection, organization, actor, "readiness.recorded", record_id, correlation, "readiness.recorded.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "readiness.recorded", write)


def set_availability(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        _visible_space(connection, body["space_id"])
        current = connection.execute(
            text(
                """
                SELECT id, availability FROM availability_statements
                WHERE organization_id = :org AND space_id = :space AND current
                """
            ),
            {"org": organization, "space": body["space_id"]},
        ).mappings().first()
        previous = current["availability"] if current else "not_offered"
        nxt = body["availability"]
        if current and nxt not in AVAILABILITY_TRANSITIONS[previous]:
            raise CommandError(422, "invalid_transition", "That availability transition is not allowed")
        if current:
            connection.execute(text("UPDATE availability_statements SET current = false WHERE id = :id"), {"id": current["id"]})
        record_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO availability_statements (
                  organization_id, id, space_id, availability, effective_on, confidence, source, confirmed_at, reason
                ) VALUES (
                  :org, :id, :space, :availability, :effective, :confidence, :source, now(), :reason
                )
                """
            ),
            {
                "org": organization,
                "id": record_id,
                "space": body["space_id"],
                "availability": nxt,
                "effective": body["effective_on"],
                "confidence": body["confidence"],
                "source": body["source"],
                "reason": body["reason"],
            },
        )
        result = {"id": str(record_id), "availability": nxt, "previous": previous, "synthetic": True}
        _audit_outbox(connection, organization, actor, "availability.recorded", record_id, correlation, "availability.recorded.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "availability.recorded", write)


def apply_asking_price(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        _visible_space(connection, body["space_id"])
        role = _role(connection, actor)
        current = connection.execute(
            text(
                """
                SELECT id, amount_minor FROM asking_prices
                WHERE organization_id = :org AND space_id = :space AND ended_on IS NULL
                """
            ),
            {"org": organization, "space": body["space_id"]},
        ).mappings().first()
        previous = int(current["amount_minor"]) if current else int(body["amount_minor"])
        proposed = int(body["amount_minor"])
        material = current is not None and _material(previous, proposed)
        if material and role != "owner":
            exception_id = uuid4()
            connection.execute(
                text(
                    """
                    INSERT INTO pricing_exceptions (
                      organization_id, id, space_id, proposed_amount_minor, reason, status, actor_id
                    ) VALUES (:org, :id, :space, :amount, :reason, 'prepared', :actor)
                    """
                ),
                {"org": organization, "id": exception_id, "space": body["space_id"], "amount": proposed, "reason": body["reason"], "actor": actor},
            )
            result = {"id": str(exception_id), "status": "prepared", "applied": False, "synthetic": True}
            _audit_outbox(connection, organization, actor, "pricing.exception_prepared", exception_id, correlation, "pricing.exception_prepared.v1", result)
            return result
        if current:
            connection.execute(
                text("UPDATE asking_prices SET ended_on = :effective WHERE id = :id"),
                {"effective": body["effective_on"], "id": current["id"]},
            )
        price_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO asking_prices (
                  organization_id, id, space_id, amount_minor, currency, period, effective_on, reason, actor_id, approval_state
                ) VALUES (
                  :org, :id, :space, :amount, :currency, :period, :effective, :reason, :actor, :approval
                )
                """
            ),
            {
                "org": organization,
                "id": price_id,
                "space": body["space_id"],
                "amount": proposed,
                "currency": body.get("currency", "USD"),
                "period": body.get("period", "monthly"),
                "effective": body["effective_on"],
                "reason": body["reason"],
                "actor": actor,
                "approval": "owner_approved" if material else "routine",
            },
        )
        result = {"id": str(price_id), "amount_minor": proposed, "applied": True, "approval_state": "owner_approved" if material else "routine", "synthetic": True}
        _audit_outbox(connection, organization, actor, "pricing.asking_recorded", price_id, correlation, "pricing.asking_recorded.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "pricing.asking_recorded", write)


def place_hold(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        _visible_space(connection, body["space_id"])
        hold_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO availability_holds (organization_id, id, space_id, reason, holder_label, expires_at)
                VALUES (:org, :id, :space, :reason, :holder, :expires)
                """
            ),
            {"org": organization, "id": hold_id, "space": body["space_id"], "reason": body["reason"], "holder": body["holder_label"], "expires": body["expires_at"]},
        )
        job_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO phase8_jobs (organization_id, id, job_kind, aggregate_id, status, available_at, idempotency_key)
                VALUES (:org, :id, 'hold_expiry', :hold, 'pending', :expires, :key)
                """
            ),
            {"org": organization, "id": job_id, "hold": hold_id, "expires": body["expires_at"], "key": f"hold-expiry:{hold_id}"},
        )
        result = {"id": str(hold_id), "job_id": str(job_id), "status": "open", "synthetic": True}
        _audit_outbox(connection, organization, actor, "availability.hold_placed", hold_id, correlation, "availability.hold_placed.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "availability.hold_placed", write)


def release_due_holds(settings, actor, organization) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, "property.manage")
        rows = connection.execute(
            text(
                """
                UPDATE availability_holds
                SET released_at = now()
                WHERE organization_id = :org AND released_at IS NULL AND expires_at <= now()
                RETURNING id
                """
            ),
            {"org": organization},
        ).all()
        for row in rows:
            connection.execute(
                text(
                    """
                    UPDATE phase8_jobs
                    SET status = 'done'
                    WHERE organization_id = :org AND job_kind = 'hold_expiry' AND status = 'pending'
                      AND aggregate_id = :hold
                    """
                ),
                {"org": organization, "hold": row.id},
            )
    return {"released": len(rows), "synthetic": True}


def register_media(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        _visible_space(connection, body["space_id"])
        raw = body["content"]
        rejected = (
            "EICAR" in raw
            or "<script" in raw.lower()
            or raw.startswith("<svg")
            or body["declared_mime"] not in {"image/jpeg", "image/png", "image/webp"}
            or not raw.startswith(body["signature"])
        )
        status = "rejected" if rejected or body.get("rights_state") != "licensed" or not body.get("alt_text") else "approved"
        review = "rejected" if status == "rejected" else "approved"
        asset_id = uuid4()
        if status == "approved":
            connection.execute(
                text(
                    """
                    UPDATE listing_media_assets
                    SET primary_asset = false
                    WHERE organization_id = :org AND space_id = :space AND primary_asset
                    """
                ),
                {"org": organization, "space": body["space_id"]},
            )
        connection.execute(
            text(
                """
                INSERT INTO listing_media_assets (
                  organization_id, id, space_id, status, declared_mime, content_sha256, alt_text,
                  rights_state, review_state, sort_order, primary_asset
                ) VALUES (
                  :org, :id, :space, :status, :mime, :digest, :alt, :rights, :review, :sort, :primary
                )
                """
            ),
            {
                "org": organization,
                "id": asset_id,
                "space": body["space_id"],
                "status": status,
                "mime": body["declared_mime"],
                "digest": hashlib.sha256(raw.encode()).hexdigest(),
                "alt": body.get("alt_text") or "",
                "rights": body.get("rights_state") or "unknown",
                "review": review,
                "sort": int(body.get("sort_order") or 0),
                "primary": status == "approved",
            },
        )
        result = {"id": str(asset_id), "status": status, "review_state": review, "synthetic": True}
        _audit_outbox(connection, organization, actor, "media.reviewed", asset_id, correlation, "media.reviewed.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "media.reviewed", write)


def publish_snapshot(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        listing = connection.execute(
            text(
                """
                SELECT listing.id, listing.version, listing.space_id, listing.property_name, listing.label,
                       listing.municipality, listing.state, listing.availability, listing.publication,
                       state.version AS space_version
                FROM listings listing
                JOIN space_states state ON state.organization_id = listing.organization_id
                  AND state.space_id = listing.space_id AND state.current
                WHERE listing.organization_id = :org AND listing.id = :id
                """
            ),
            {"org": organization, "id": body["listing_id"]},
        ).mappings().first()
        if not listing:
            raise CommandError(404, "not_found", "Listing was not found")
        if int(listing["version"]) != int(body["expected_version"]):
            raise CommandError(409, "stale_version", "The listing changed. Reload and try again.", retryable=True)
        blockers = []
        if listing["availability"] != "offerable":
            blockers.append("availability")
        price = connection.execute(
            text(
                """
                SELECT amount_minor, currency FROM asking_prices
                WHERE organization_id = :org AND space_id = :space AND ended_on IS NULL
                """
            ),
            {"org": organization, "space": listing["space_id"]},
        ).mappings().first()
        if not price:
            blockers.append("asking_price")
        media = connection.execute(
            text(
                """
                SELECT alt_text FROM listing_media_assets
                WHERE organization_id = :org AND space_id = :space AND status = 'approved' AND primary_asset
                """
            ),
            {"org": organization, "space": listing["space_id"]},
        ).mappings().first()
        if not media:
            blockers.append("primary_media")
        hold = connection.execute(
            text(
                """
                SELECT id FROM availability_holds
                WHERE organization_id = :org AND space_id = :space AND released_at IS NULL AND expires_at > now()
                """
            ),
            {"org": organization, "space": listing["space_id"]},
        ).first()
        if hold:
            blockers.append("open_hold")
        description = body.get("description") or "EXAMPLE ONLY. Synthetic listing facts."
        if any(phrase in description.lower() for phrase in PROHIBITED):
            blockers.append("fair_housing_review")
        if blockers:
            raise CommandError(422, "publication_blocked", "Publication is blocked: " + ", ".join(blockers))
        fees = connection.execute(
            text(
                """
                SELECT COALESCE(sum(amount_minor), 0) FROM fee_components
                WHERE organization_id = :org AND space_id = :space AND ended_on IS NULL AND required
                """
            ),
            {"org": organization, "space": listing["space_id"]},
        ).scalar()
        payload = {
            "property_name": listing["property_name"],
            "label": listing["label"],
            "municipality": listing["municipality"],
            "state": listing["state"],
            "availability": "available",
            "amount_minor": int(price["amount_minor"]),
            "currency": price["currency"],
            "estimate_minor": int(price["amount_minor"]) + int(fees or 0),
            "estimate_disclaimer": "EXAMPLE ONLY. This is a listing estimate, not a resident ledger balance.",
            "alt_text": media["alt_text"],
            "description": description,
            "synthetic": True,
            "schema_version": 1,
        }
        if FORBIDDEN_PUBLIC & set(payload):
            raise CommandError(422, "projection_rejected", "The public projection contains a prohibited field")
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha256(encoded.encode()).hexdigest()
        slug = body["public_slug"]
        connection.execute(
            text("UPDATE listing_snapshots SET superseded_at = now() WHERE organization_id = :org AND public_slug = :slug AND superseded_at IS NULL"),
            {"org": organization, "slug": slug},
        )
        snapshot_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO listing_snapshots (
                  organization_id, id, listing_id, space_id, public_slug, schema_version, content_hash, payload, actor_id
                ) VALUES (
                  :org, :id, :listing, :space, :slug, 1, :digest, CAST(:payload AS jsonb), :actor
                )
                """
            ),
            {
                "org": organization,
                "id": snapshot_id,
                "listing": listing["id"],
                "space": listing["space_id"],
                "slug": slug,
                "digest": digest,
                "payload": encoded,
                "actor": actor,
            },
        )
        updated = connection.execute(
            text("UPDATE listings SET publication = 'published', public_slug = :slug, version = version + 1 WHERE organization_id = :org AND id = :id AND version = :expected RETURNING version"),
            {"slug": slug, "org": organization, "id": listing["id"], "expected": body["expected_version"]},
        ).first()
        if not updated:
            raise CommandError(409, "stale_version", "The listing changed. Reload and try again.", retryable=True)
        result = {"id": str(snapshot_id), "public_slug": slug, "content_hash": digest, "version": updated.version, "synthetic": True}
        _audit_outbox(connection, organization, actor, "listing.snapshot_published", snapshot_id, correlation, "listing.snapshot_published.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "listing.snapshot_published", write)


def unpublish_snapshot(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        row = connection.execute(
            text(
                """
                UPDATE listing_snapshots SET superseded_at = now()
                WHERE organization_id = :org AND public_slug = :slug AND superseded_at IS NULL
                RETURNING id
                """
            ),
            {"org": organization, "slug": body["public_slug"]},
        ).first()
        if not row:
            raise CommandError(404, "not_found", "Published snapshot was not found")
        connection.execute(
            text("UPDATE listings SET publication = 'unpublished', version = version + 1 WHERE organization_id = :org AND public_slug = :slug"),
            {"org": organization, "slug": body["public_slug"]},
        )
        result = {"id": str(row.id), "publication": "unpublished", "synthetic": True}
        _audit_outbox(connection, organization, actor, "listing.snapshot_unpublished", row.id, correlation, "listing.snapshot_unpublished.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "listing.snapshot_unpublished", write)


def public_snapshot(settings, slug: str):
    from .db import runtime_transaction

    with runtime_transaction(settings, None, None, uuid4()) as connection:
        payload = connection.execute(text("SELECT perchpoint.published_listing_snapshot(:slug)"), {"slug": slug}).scalar()
    if isinstance(payload, str):
        return json.loads(payload)
    return payload


def archive_property(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        published = connection.execute(
            text(
                """
                SELECT listing.id FROM listings listing
                JOIN spaces space ON space.organization_id = listing.organization_id AND space.id = listing.space_id
                WHERE listing.organization_id = :org AND space.property_id = :property AND listing.publication = 'published'
                """
            ),
            {"org": organization, "property": body["property_id"]},
        ).first()
        if published:
            raise CommandError(409, "archive_blocked", "Unpublish the listing before archiving this property")
        row = connection.execute(
            text(
                """
                UPDATE properties SET lifecycle = 'archived', version = version + 1
                WHERE organization_id = :org AND id = :id AND version = :expected
                RETURNING version
                """
            ),
            {"org": organization, "id": body["property_id"], "expected": body["expected_version"]},
        ).first()
        if not row:
            raise CommandError(409, "stale_version", "The property changed. Reload and try again.", retryable=True)
        result = {"id": str(body["property_id"]), "lifecycle": "archived", "version": row.version, "synthetic": True}
        _audit_outbox(connection, organization, actor, "property.archived", UUID(str(body["property_id"])), correlation, "property.archived.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "property.archived", write)


def bulk_dry_run(settings, actor, organization, body) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, "property.manage")
        rows = connection.execute(
            text(
                """
                SELECT space.id, space.label FROM spaces space
                WHERE space.organization_id = :org AND space.id = ANY(:ids)
                """
            ),
            {"org": organization, "ids": body["space_ids"]},
        ).mappings().all()
    found = {str(row["id"]) for row in rows}
    eligible = [{"space_id": str(row["id"]), "label": row["label"], "amount_minor": body["amount_minor"]} for row in rows]
    ineligible = [{"space_id": item, "reason": "outside_scope"} for item in body["space_ids"] if item not in found]
    return {"eligible": eligible, "ineligible": ineligible, "applied": False, "synthetic": True}


def bulk_apply(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        role = _role(connection, actor)
        results = []
        for space_id in body["space_ids"]:
            visible = connection.execute(text("SELECT id FROM spaces WHERE id = :space"), {"space": space_id}).first()
            if not visible:
                results.append({"space_id": space_id, "applied": False, "reason": "outside_scope"})
                continue
            current = connection.execute(
                text("SELECT id, amount_minor FROM asking_prices WHERE organization_id = :org AND space_id = :space AND ended_on IS NULL"),
                {"org": organization, "space": space_id},
            ).mappings().first()
            proposed = int(body["amount_minor"])
            if current and _material(int(current["amount_minor"]), proposed) and role != "owner":
                results.append({"space_id": space_id, "applied": False, "reason": "owner_exception"})
                continue
            if current:
                connection.execute(
                    text("UPDATE asking_prices SET ended_on = :effective WHERE id = :id"),
                    {"effective": body["effective_on"], "id": current["id"]},
                )
            price_id = uuid4()
            connection.execute(
                text(
                    """
                    INSERT INTO asking_prices (
                      organization_id, id, space_id, amount_minor, currency, period, effective_on, reason, actor_id, approval_state
                    ) VALUES (
                      :org, :id, :space, :amount, 'USD', 'monthly', :effective, :reason, :actor, 'routine'
                    )
                    """
                ),
                {"org": organization, "id": price_id, "space": space_id, "amount": proposed, "effective": body["effective_on"], "reason": body["reason"], "actor": actor},
            )
            results.append({"space_id": space_id, "applied": True, "id": str(price_id)})
        result = {"results": results, "applied": True, "synthetic": True}
        _audit_outbox(connection, organization, actor, "pricing.bulk_applied", uuid4(), correlation, "pricing.bulk_applied.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "pricing.bulk_applied", write)


def record_fee(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        _visible_space(connection, body["space_id"])
        fee_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO fee_components (
                  organization_id, id, space_id, code, label, amount_minor, currency, required, recurring, refundable, effective_on
                ) VALUES (
                  :org, :id, :space, :code, :label, :amount, :currency, :required, :recurring, :refundable, :effective
                )
                """
            ),
            {
                "org": organization,
                "id": fee_id,
                "space": body["space_id"],
                "code": body["code"],
                "label": body["label"],
                "amount": body["amount_minor"],
                "currency": body.get("currency", "USD"),
                "required": body["required"],
                "recurring": body["recurring"],
                "refundable": body["refundable"],
                "effective": body["effective_on"],
            },
        )
        result = {"id": str(fee_id), "synthetic": True}
        _audit_outbox(connection, organization, actor, "pricing.fee_recorded", fee_id, correlation, "pricing.fee_recorded.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "pricing.fee_recorded", write)

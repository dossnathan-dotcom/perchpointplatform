"""Phase 9 discovery projections for HawkVision-owned surfaces.

Search reads immutable Phase 8 snapshots. External syndication stays disabled.
This module does not create inquiries, showings, applications, or leases.
"""
from __future__ import annotations

import hashlib
import hmac
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
CLASSIFICATIONS = {"bot", "health", "test", "preview", "staff"}
ASSISTANCE = {"assistance", "assistance_animal", "service_animal"}
ZONE = "America/New_York"


def _require(connection, capability: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise CommandError(403, "denied", "This action is not authorized")


def _role(connection) -> str:
    return connection.execute(text("SELECT perchpoint.role_for_account(perchpoint.current_actor())")).scalar() or ""


def _optional_number(value, kind: str):
    if value in (None, ""):
        return None
    try:
        number = float(value) if kind == "float" else int(value)
    except (TypeError, ValueError) as exc:
        raise CommandError(422, "rejected", "A discovery measurement was not a number") from exc
    return number


def _tokens(values, label: str) -> list[str]:
    if not values:
        return []
    if not isinstance(values, list) or len(values) > 12:
        raise CommandError(422, "rejected", f"{label} is outside the allowed set")
    cleaned = []
    for item in values:
        token = str(item).strip().lower()
        if not re.fullmatch(r"[a-z0-9_]{1,40}", token):
            raise CommandError(422, "rejected", f"{label} contains an unsupported value")
        cleaned.append(token)
    return cleaned


def _pg_array(values: list[str]) -> str:
    return "{" + ",".join(values) + "}"


def _public_point(value):
    number = _optional_number(value, "float")
    if number is None:
        return None
    return round(number, 3)


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
        "accessibility_note": "Verified feature only. This is not a compliance or suitability determination.",
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
        pet_policy = str(body.get("pet_policy") or "")
        if pet_policy in ASSISTANCE:
            raise CommandError(422, "pet_policy_rejected", "Assistance animals are outside ordinary pet filters")
        amenities = _tokens(body.get("amenities") or [], "Amenities")
        features = _tokens(body.get("accessibility_features") or [], "Accessibility features")
        if features and not body.get("verification_on"):
            raise CommandError(422, "verification_required", "An accessibility feature needs a verification date")
        payload = _public_payload(snapshot["payload"], snapshot["use"] or "residential")
        payload.update({
            "neighborhood": body.get("neighborhood") or "",
            "postal_code": body.get("postal_code") or "",
            "pet_policy": pet_policy,
            "amenities": amenities,
            "accessibility_features": features,
            "verification_on": body.get("verification_on") or "",
            "latitude": _public_point(body.get("latitude")),
            "longitude": _public_point(body.get("longitude")),
            "location_precision": "public_3dp",
        })
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
                  content_hash, eligibility, payload, search_text, city, neighborhood, postal_code, use_code,
                  amount_minor, currency, period, bedrooms, bathrooms, area_sqft, pet_policy, amenities,
                  accessibility_features, latitude, longitude, available_on, sort_rank, version
                ) VALUES (
                  :org, :id, :listing, :snapshot, :slug, 1, 1, :digest, 'eligible', CAST(:payload AS jsonb),
                  :search, :city, :neighborhood, :postal, :use, :amount, :currency, 'monthly', :beds, :baths,
                  :area, :pet, CAST(:amenities AS text[]), CAST(:features AS text[]), :latitude, :longitude,
                  :available, :rank, :version
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
                "beds": _optional_number(body.get("bedrooms"), "int"),
                "baths": _optional_number(body.get("bathrooms"), "float"),
                "area": _optional_number(body.get("area_sqft"), "int"),
                "neighborhood": body.get("neighborhood") or "",
                "postal": body.get("postal_code") or "",
                "pet": pet_policy,
                "amenities": _pg_array(amenities),
                "features": _pg_array(features),
                "latitude": payload["latitude"],
                "longitude": payload["longitude"],
                "available": body.get("available_on") or None,
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
                      :org, :id, :projection, :target, 'publish', :key, :fingerprint, :version, 10, 'pending', :digest
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
                SET eligibility = 'withdrawn', version = version + 1, marketed_through = COALESCE(marketed_through, now())
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


def claim_job(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        row = connection.execute(
            text(
                """
                UPDATE distribution_operations
                SET state = 'leased', attempts = attempts + 1, lease_owner = :actor,
                    lease_expires = now() + interval '30 seconds'
                WHERE organization_id = :org AND id = (
                  SELECT id FROM distribution_operations
                  WHERE organization_id = :org
                    AND (CAST(:projection AS uuid) IS NULL OR projection_id = CAST(:projection AS uuid))
                    AND (state = 'pending' OR (state = 'leased' AND lease_expires < now()))
                  ORDER BY priority ASC, id
                  FOR UPDATE SKIP LOCKED
                  LIMIT 1
                )
                RETURNING id, projection_id, projection_version, attempts, state, target_code
                """
            ),
            {"org": organization, "actor": str(actor), "projection": body.get("projection_id")},
        ).mappings().first()
        result = {"claimed": bool(row), "synthetic": True}
        if row:
            result.update({"id": str(row["id"]), "projection_id": str(row["projection_id"]), "projection_version": int(row["projection_version"]), "attempts": int(row["attempts"]), "state": row["state"], "target_code": row["target_code"]})
        _audit_outbox(connection, organization, actor, "discovery.job_claimed", row["id"] if row else uuid4(), correlation, "discovery.job_claimed.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "discovery.job_claimed", write)


def complete_job(settings, actor, organization, body, key, correlation) -> dict:
    def write(connection, _fp):
        _require(connection, "property.manage")
        row = connection.execute(
            text(
                """
                SELECT operation.id, operation.projection_version, operation.state, projection.version AS current_version
                FROM distribution_operations operation
                JOIN discovery_projections projection
                  ON projection.organization_id = operation.organization_id AND projection.id = operation.projection_id
                WHERE operation.organization_id = :org AND operation.id = :id
                """
            ),
            {"org": organization, "id": body["operation_id"]},
        ).mappings().first()
        if not row:
            raise CommandError(404, "not_found", "Distribution operation was not found")
        if int(body["expected_version"]) != int(row["current_version"]):
            connection.execute(
                text("UPDATE distribution_operations SET state = 'stale', last_error = 'stale_version' WHERE organization_id = :org AND id = :id"),
                {"org": organization, "id": row["id"]},
            )
            result = {"id": str(row["id"]), "state": "stale", "synthetic": True}
        elif body.get("terminal"):
            connection.execute(
                text("UPDATE distribution_operations SET state = 'dead_letter', last_error = 'terminal' WHERE organization_id = :org AND id = :id"),
                {"org": organization, "id": row["id"]},
            )
            result = {"id": str(row["id"]), "state": "dead_letter", "next_action": "Replay only after the blocker is corrected.", "synthetic": True}
        else:
            connection.execute(
                text("UPDATE distribution_operations SET state = 'done', lease_expires = NULL WHERE organization_id = :org AND id = :id AND projection_version = :version"),
                {"org": organization, "id": row["id"], "version": row["current_version"]},
            )
            result = {"id": str(row["id"]), "state": "done", "synthetic": True}
        _audit_outbox(connection, organization, actor, "discovery.job_completed", row["id"], correlation, "discovery.job_completed.v1", result)
        return result

    return _command(settings, actor, organization, key, body, correlation, "discovery.job_completed", write)


def marketed_interval(settings, actor, organization, slug: str) -> dict:
    from .db import runtime_transaction

    with runtime_transaction(settings, actor, organization, uuid4()) as connection:
        _require(connection, "property.read")
        row = connection.execute(
            text(
                """
                SELECT eligibility,
                       (timezone(:zone, COALESCE(marketed_through, now()))::date - timezone(:zone, created_at)::date) AS cumulative
                FROM discovery_projections
                WHERE public_slug = :slug AND current
                """
            ),
            {"slug": slug, "zone": ZONE},
        ).mappings().first()
    if not row:
        raise CommandError(404, "not_found", "Discovery projection was not found")
    cumulative = int(row["cumulative"] or 0)
    episode = 0 if row["eligibility"] != "eligible" else cumulative
    return {"episode_days": episode, "cumulative_days": cumulative, "timezone": ZONE, "eligibility": row["eligibility"], "synthetic": True}


def _canonical(criteria: dict) -> str:
    return "&".join(f"{key}={criteria[key]}" for key in sorted(criteria))


def search_public(settings, criteria: dict) -> dict:
    from .db import runtime_transaction

    safe = {key: str(value) for key, value in criteria.items() if value not in (None, "")}
    for token in PROHIBITED_CHANNELS:
        if token in json.dumps(safe).lower():
            raise CommandError(400, "rejected", "That search is not available")
    query = safe.get("query", "")
    if len(query) > 80 or len(safe) > 16:
        raise CommandError(400, "rejected", "The search is too long")
    safe["query"] = re.sub(r"[%_]", "", query)
    if "query" in safe and safe["query"] == "":
        safe.pop("query")
    for key in ("origin_lat", "origin_lon", "radius_km"):
        if key in safe:
            _optional_number(safe[key], "float")
    if "radius_km" in safe and float(safe["radius_km"]) > 50:
        raise CommandError(400, "rejected", "The search radius is outside the public limit")
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        payload = connection.execute(text("SELECT perchpoint.search_discovery(CAST(:criteria AS jsonb))"), {"criteria": json.dumps(safe)}).scalar()
    if isinstance(payload, str):
        payload = json.loads(payload)
    payload = payload or {"total": 0, "records": [], "facets": {"residential": 0, "commercial": 0}}
    payload["canonical_query"] = _canonical({key: safe[key] for key in safe if key != "query" or safe.get("query")})
    payload["synthetic"] = True
    if int(payload.get("total") or 0) == 0:
        payload["zero_result"] = {
            "constraints": sorted(key for key in safe if key not in {"limit", "offset", "sort"}),
            "relaxation": "Remove one criterion and search again. Discovery does not broaden a query on its own.",
        }
    return payload


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
    classification = str(body.get("classification") or "")
    if classification and classification not in CLASSIFICATIONS:
        raise CommandError(422, "rejected", "That traffic classification is not recognized")
    with runtime_transaction(settings, None, None, uuid4()) as connection:
        payload = connection.execute(
            text(
                """
                SELECT perchpoint.record_discovery_event(:slug, :name, :session, :source, :medium, :campaign, :key, :gpc, :classification)
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
                "classification": classification,
            },
        ).scalar()
    if isinstance(payload, str):
        payload = json.loads(payload)
    if not payload or payload.get("found") is False:
        raise CommandError(404, "not_found", "That listing is not in discovery")
    payload["synthetic"] = True
    payload.pop("found", None)
    if body.get("event_name") == "cta" and payload.get("counted") is not False:
        material = f"{body.get('listing_slug')}|{body.get('source')}|{body.get('medium')}|{body.get('campaign')}"
        payload["handoff_ref"] = hmac.new(settings.jwt_secret.encode(), material.encode(), hashlib.sha256).hexdigest()
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

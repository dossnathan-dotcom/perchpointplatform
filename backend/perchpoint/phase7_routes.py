"""Phase 7 public content and governed intake. Listing facts stay read-only."""
from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import datetime, timezone
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import text

from .db import runtime_transaction
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")

_UNSAFE = re.compile(r"<\s*script|javascript:|onerror\s*=|onload\s*=|data:text/html", re.I)
_INTENTS = {
    "rental_inquiry",
    "application_help",
    "resident_help",
    "maintenance_routing",
    "vendor_business",
    "accessibility",
    "general",
}
_FIELDS = {"name", "email", "message", "company_website", "listing_slug"}
_EVENTS = {
    "page_view", "listing_view", "cta", "inquiry_start", "inquiry_validation",
    "inquiry_submit", "apply_route", "support_intent", "maintenance_intent",
    "contact_category", "sign_in_transition", "delivery_failure",
}
_HITS: dict[str, list[float]] = {}
_PUBLIC_CACHE: dict[str, dict] = {}
_REQUIRED_SLUGS = {"privacy", "terms", "contact", "maintenance", "apply"}


def _limited(key: str, limit: int = 30) -> bool:
    now = time.monotonic()
    recent = [stamp for stamp in _HITS.get(key, []) if now - stamp < 60]
    if len(recent) >= limit:
        _HITS[key] = recent
        return True
    recent.append(now)
    _HITS[key] = recent
    return False


class DraftBody(BaseModel):
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$", max_length=80)
    title: str = Field(min_length=2, max_length=140)
    body: str = Field(min_length=2, max_length=4000)
    kind: str = Field(pattern=r"^(page|faq|resource|announcement|legal|navigation|channel)$")
    risk_class: str = Field(pattern=r"^(routine|elevated)$")
    reason: str = Field(min_length=2, max_length=240)


class PublishBody(BaseModel):
    expected_version: int = Field(ge=1)


class RevisionBody(BaseModel):
    expected_version: int = Field(ge=1)
    title: str = Field(min_length=2, max_length=140)
    body: str = Field(min_length=2, max_length=4000)
    reason: str = Field(min_length=2, max_length=240)


class RollbackBody(BaseModel):
    expected_version: int = Field(ge=1)
    revision_id: UUID
    reason: str = Field(min_length=2, max_length=240)


class ScheduleBody(BaseModel):
    expected_version: int = Field(ge=1)
    run_at: str
    time_zone: str = "America/New_York"
    action: str = "publish"


class RedirectBody(BaseModel):
    source_path: str = Field(min_length=2, max_length=160)
    destination_path: str = Field(min_length=2, max_length=160)
    status_code: int


class AnalyticsBody(BaseModel):
    name: str
    consent: str
    properties: dict[str, str] = Field(default_factory=dict)
    analytics_allowed: bool = False


class SubmissionBody(BaseModel):
    intent: str
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=3, max_length=160)
    message: str = Field(min_length=2, max_length=2000)
    consent_version: str = Field(min_length=2, max_length=40)
    source_page: str = Field(min_length=1, max_length=160)
    listing_slug: str | None = Field(default=None, max_length=80)
    first_touch: str | None = Field(default=None, max_length=120)
    last_touch: str | None = Field(default=None, max_length=120)
    idempotency_key: str = Field(min_length=8, max_length=128)
    company_website: str | None = None
    attachment: str | None = None


def _reject_unsafe(value: str) -> None:
    if _UNSAFE.search(value):
        raise HTTPException(400, {"code": "unsafe_content", "message": "That content cannot be saved.", "retryable": False})


def _public_path(value: str) -> None:
    if not value.startswith("/") or value.startswith("//") or "\\" in value or "://" in value:
        raise HTTPException(400, {"code": "rejected", "message": "That address cannot be used.", "retryable": False})


def _blocks(title: str, body: str) -> dict:
    _reject_unsafe(title)
    _reject_unsafe(body)
    return {"schema": 1, "title": title, "blocks": [{"type": "prose", "text": body}]}


def _public_document(row: dict) -> dict:
    if isinstance(row, str):
        row = json.loads(row)
    snapshot = row.get("snapshot") or {}
    title = snapshot.get("title") or row.get("slug")
    row["canonical"] = f"/{row['slug']}"
    row["structured_data"] = {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "name": title,
        "url": row["canonical"],
    }
    return row


@router.get("/public/pages/{slug}")
def public_page(slug: str, response: Response, current_settings: Settings = Depends(settings)):
    cached = _PUBLIC_CACHE.get(slug)
    if cached is not None:
        response.headers["Cache-Control"] = "public, max-age=60"
        response.headers["X-Robots-Tag"] = "index, follow"
        return cached
    with runtime_transaction(current_settings, None, None, uuid4()) as connection:
        row = connection.execute(text("SELECT perchpoint.published_page(:slug)"), {"slug": slug}).scalar()
    if not row:
        _PUBLIC_CACHE.pop(slug, None)
        raise HTTPException(404, {"code": "not_found", "message": "That page is not published.", "retryable": False})
    document = _public_document(row)
    _PUBLIC_CACHE[slug] = document
    response.headers["Cache-Control"] = "public, max-age=60"
    response.headers["X-Robots-Tag"] = "index, follow"
    return document


@router.get("/public/navigation")
def public_navigation(current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, None, None, uuid4()) as connection:
        rows = connection.execute(text("SELECT perchpoint.published_navigation()")).scalar()
    return {"pages": rows or [], "synthetic": True}


@router.get("/public/sitemap.xml")
def public_sitemap(current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, None, None, uuid4()) as connection:
        rows = connection.execute(text("SELECT perchpoint.published_navigation()")).scalar() or []
    body = "".join(f"<url><loc>/{item['slug']}</loc></url>" for item in rows)
    return {"xml": f"<urlset>{body}</urlset>", "synthetic": True}


@router.get("/public/robots.txt")
def public_robots():
    body = "\n".join([
        "User-agent: *",
        "Allow: /",
        "Disallow: /staff/",
        "Disallow: /sign-in",
        "Disallow: /api/",
        "Disallow: /preview",
    ])
    return Response(body, media_type="text/plain")


@router.get("/public/redirect")
def public_redirect(path: str, current_settings: Settings = Depends(settings)):
    _public_path(path)
    with runtime_transaction(current_settings, None, None, uuid4()) as connection:
        row = connection.execute(text("SELECT perchpoint.published_redirect(:path)"), {"path": path}).scalar()
    if not row:
        raise HTTPException(404, {"code": "not_found", "message": "That address is not redirected.", "retryable": False})
    return row


@router.post("/public/submissions", status_code=201)
def public_submission(body: SubmissionBody, request: Request, current_settings: Settings = Depends(settings)):
    if _limited(f"submission:{body.intent}:{request.client.host if request.client else 'local'}"):
        raise HTTPException(429, {"code": "rate_limited", "message": "Too many requests. Wait and try again.", "retryable": True})
    if body.intent not in _INTENTS:
        raise HTTPException(400, {"code": "rejected", "message": "The inquiry was not accepted.", "retryable": False})
    if body.attachment:
        raise HTTPException(400, {"code": "attachments_rejected", "message": "Attachments are not accepted here.", "retryable": False})
    payload = {key: value for key, value in body.model_dump().items() if key in _FIELDS and value}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()
    try:
        with runtime_transaction(current_settings, None, None, uuid4()) as connection:
            row = connection.execute(
                text(
                    """
                    SELECT perchpoint.accept_public_submission(
                      :intent, CAST(:payload AS jsonb), :consent, :source, :listing,
                      :first_touch, :last_touch, :key, :hash, :correlation
                    )
                    """
                ),
                {
                    "intent": body.intent,
                    "payload": json.dumps(payload),
                    "consent": body.consent_version,
                    "source": body.source_page,
                    "listing": body.listing_slug,
                    "first_touch": body.first_touch,
                    "last_touch": body.last_touch,
                    "key": body.idempotency_key,
                    "hash": digest,
                    "correlation": uuid4(),
                },
            ).scalar()
    except Exception as exc:
        message = str(getattr(exc, "orig", exc))
        if "listing_unavailable" in message:
            raise HTTPException(409, {"code": "listing_unavailable", "message": "That home is not available for a new inquiry.", "retryable": False}) from exc
        if "idempotency_conflict" in message:
            raise HTTPException(409, {"code": "idempotency_conflict", "message": "That submission key was already used.", "retryable": False}) from exc
        if "attachments_rejected" in message or "rejected" in message:
            raise HTTPException(400, {"code": "rejected", "message": "The inquiry was not accepted.", "retryable": False}) from exc
        raise HTTPException(503, {"code": "unavailable", "message": "The inquiry was not saved.", "retryable": True}) from exc
    return {
        "reference": row["reference"],
        "replayed": row["replayed"],
        "message": "HawkVision received this request. This is not an approval, a reservation, or an emergency response.",
        "synthetic": True,
        "request_id": request.headers.get("x-request-id"),
    }


@router.post("/public/analytics", status_code=202)
def public_analytics(body: AnalyticsBody, request: Request, current_settings: Settings = Depends(settings)):
    if body.name not in _EVENTS or body.consent not in {"essential", "optional"}:
        raise HTTPException(400, {"code": "rejected", "message": "That event was not accepted.", "retryable": False})
    preference = request.headers.get("sec-gpc") == "1"
    if body.consent == "optional" and (preference or not body.analytics_allowed):
        return {"stored": False, "reason": "preference", "synthetic": True}
    properties = {key: value[:80] for key, value in body.properties.items() if key.isidentifier() and len(key) <= 40}
    try:
        with runtime_transaction(current_settings, None, None, uuid4()) as connection:
            row = connection.execute(
                text("SELECT perchpoint.record_public_analytics(:name, :consent, CAST(:properties AS jsonb))"),
                {"name": body.name, "consent": body.consent, "properties": json.dumps(properties)},
            ).scalar()
    except Exception as exc:
        message = str(getattr(exc, "orig", exc))
        if "pii_rejected" in message or "rejected" in message:
            raise HTTPException(400, {"code": "rejected", "message": "That event was not accepted.", "retryable": False}) from exc
        raise HTTPException(503, {"code": "unavailable", "message": "The event was not saved.", "retryable": True}) from exc
    return row


@router.post("/content/redirects", status_code=201)
def create_redirect(body: RedirectBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    _public_path(body.source_path)
    _public_path(body.destination_path)
    if body.source_path == body.destination_path or body.status_code not in {301, 302, 308}:
        raise HTTPException(400, {"code": "rejected", "message": "That redirect cannot be saved.", "retryable": False})
    redirect_id = uuid4()
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        allowed = connection.execute(text("SELECT perchpoint.has_capability('content.redirect')")).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This session cannot manage redirects.", "retryable": False})
        rows = connection.execute(
            text("SELECT source_path, destination_path FROM content_redirects WHERE organization_id = :org"),
            {"org": current["organization_id"]},
        ).mappings().all()
        graph = {row["source_path"]: row["destination_path"] for row in rows}
        if body.source_path in graph:
            raise HTTPException(409, {"code": "conflict", "message": "That source already redirects.", "retryable": False})
        cursor: str | None = body.destination_path
        for _ in range(8):
            if cursor is None:
                break
            if cursor == body.source_path:
                raise HTTPException(400, {"code": "rejected", "message": "That redirect would loop.", "retryable": False})
            cursor = graph.get(cursor)
        connection.execute(
            text(
                """
                INSERT INTO content_redirects (
                  organization_id, id, source_path, destination_path, status_code, actor_id
                ) VALUES (:org, :id, :source, :destination, :status, :actor)
                """
            ),
            {
                "org": current["organization_id"],
                "id": redirect_id,
                "source": body.source_path,
                "destination": body.destination_path,
                "status": body.status_code,
                "actor": current["id"],
            },
        )
    return {"id": str(redirect_id), "synthetic": True}


@router.post("/content/drafts", status_code=201)
def create_draft(body: DraftBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    item_id = uuid4()
    revision_id = uuid4()
    blocks = _blocks(body.title, body.body)
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        allowed = connection.execute(text("SELECT perchpoint.has_capability('content.edit')")).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This session cannot edit content.", "retryable": False})
        connection.execute(
            text(
                """
                INSERT INTO content_items (
                  organization_id, id, kind, slug, risk_class, owner_account_id, status
                ) VALUES (:org, :id, :kind, :slug, :risk, :owner, 'draft')
                """
            ),
            {
                "org": current["organization_id"],
                "id": item_id,
                "kind": body.kind,
                "slug": body.slug,
                "risk": body.risk_class,
                "owner": current["id"],
            },
        )
        connection.execute(
            text(
                """
                INSERT INTO content_revisions (
                  organization_id, id, item_id, version, blocks, author_id, reason
                ) VALUES (:org, :id, :item, 1, CAST(:blocks AS jsonb), :author, :reason)
                """
            ),
            {
                "org": current["organization_id"],
                "id": revision_id,
                "item": item_id,
                "blocks": json.dumps(blocks),
                "author": current["id"],
                "reason": body.reason,
            },
        )
    return {"id": str(item_id), "revision_id": str(revision_id), "version": 1, "status": "draft", "synthetic": True}


@router.post("/content/{item_id}/publish")
def publish_item(item_id: UUID, body: PublishBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    publication_id = uuid4()
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        item = connection.execute(
            text(
                """
                SELECT id, slug, version, risk_class, status
                FROM content_items
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": item_id, "org": current["organization_id"]},
        ).mappings().first()
        if not item:
            raise HTTPException(404, {"code": "not_found", "message": "That draft is not available.", "retryable": False})
        if item["version"] != body.expected_version:
            raise HTTPException(409, {"code": "stale_version", "message": "This content changed. Reload it and try again.", "retryable": True})
        revision = connection.execute(
            text(
                """
                SELECT id, blocks FROM content_revisions
                WHERE item_id = :item AND organization_id = :org AND version = :version
                """
            ),
            {"item": item_id, "org": current["organization_id"], "version": item["version"]},
        ).mappings().first()
        if not revision:
            raise HTTPException(404, {"code": "not_found", "message": "That revision is not available.", "retryable": False})
        connection.execute(
            text(
                """
                UPDATE content_publications
                SET superseded_at = now()
                WHERE organization_id = :org AND slug = :slug AND superseded_at IS NULL
                """
            ),
            {"org": current["organization_id"], "slug": item["slug"]},
        )
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO content_publications (
                      organization_id, id, item_id, revision_id, slug, snapshot, actor_id
                    ) VALUES (
                      :org, :id, :item, :revision, :slug, CAST(:snapshot AS jsonb), :actor
                    )
                    """
                ),
                {
                    "org": current["organization_id"],
                    "id": publication_id,
                    "item": item_id,
                    "revision": revision["id"],
                    "slug": item["slug"],
                    "snapshot": json.dumps(revision["blocks"]),
                    "actor": current["id"],
                },
            )
        except Exception as exc:
            message = str(getattr(exc, "orig", exc))
            code = "denied"
            if "self_approval" in message:
                code = "self_approval_denied"
            elif "elevated" in message:
                code = "elevated_approval_required"
            raise HTTPException(403, {"code": code, "message": "This revision cannot be published.", "retryable": False}) from exc
        updated = _mark_published(connection, current["organization_id"], item_id, item["version"], item["slug"], "content.published")
    _PUBLIC_CACHE.pop(item["slug"], None)
    return {"published": True, "slug": item["slug"], "version": updated, "synthetic": True}


def _mark_published(connection, organization_id, item_id, version, slug: str, event_type: str) -> int:
    updated = connection.execute(
        text(
            """
            UPDATE content_items
            SET status = 'published', version = version + 1, scheduled_for = NULL
            WHERE id = :id AND organization_id = :org AND version = :version
            RETURNING version
            """
        ),
        {"id": item_id, "org": organization_id, "version": version},
    ).scalar()
    if updated is None:
        raise HTTPException(409, {"code": "stale_version", "message": "This content changed. Reload it and try again.", "retryable": True})
    connection.execute(
        text(
            """
            INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, available_at)
            VALUES (:org, :id, :event_type, :item, CAST(:payload AS jsonb), 'pending', now())
            """
        ),
        {
            "org": organization_id,
            "id": uuid4(),
            "event_type": event_type,
            "item": item_id,
            "payload": json.dumps({"slug": slug, "synthetic": True}),
        },
    )
    return updated


def _when(value: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HTTPException(400, {"code": "rejected", "message": "That schedule time is not valid.", "retryable": False}) from exc
    if parsed.tzinfo is None:
        raise HTTPException(400, {"code": "rejected", "message": "That schedule time needs a time zone.", "retryable": False})
    return parsed.astimezone(timezone.utc)


@router.post("/content/{item_id}/revisions", status_code=201)
def add_revision(item_id: UUID, body: RevisionBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    blocks = _blocks(body.title, body.body)
    revision_id = uuid4()
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        allowed = connection.execute(text("SELECT perchpoint.has_capability('content.edit')")).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This session cannot edit content.", "retryable": False})
        item = connection.execute(
            text("SELECT version FROM content_items WHERE id = :id AND organization_id = :org"),
            {"id": item_id, "org": current["organization_id"]},
        ).mappings().first()
        if not item:
            raise HTTPException(404, {"code": "not_found", "message": "That draft is not available.", "retryable": False})
        if item["version"] != body.expected_version:
            raise HTTPException(409, {"code": "stale_version", "message": "This content changed. Reload it and try again.", "retryable": True})
        connection.execute(
            text(
                """
                INSERT INTO content_revisions (
                  organization_id, id, item_id, version, blocks, author_id, reason
                ) VALUES (:org, :id, :item, :version, CAST(:blocks AS jsonb), :author, :reason)
                """
            ),
            {
                "org": current["organization_id"],
                "id": revision_id,
                "item": item_id,
                "version": item["version"],
                "blocks": json.dumps(blocks),
                "author": current["id"],
                "reason": body.reason,
            },
        )
    return {"id": str(revision_id), "version": body.expected_version, "synthetic": True}


@router.post("/content/{item_id}/unpublish")
def unpublish_item(item_id: UUID, body: PublishBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        allowed = connection.execute(text("SELECT perchpoint.has_capability('content.publish')")).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This session cannot unpublish content.", "retryable": False})
        item = connection.execute(
            text("SELECT slug, version FROM content_items WHERE id = :id AND organization_id = :org"),
            {"id": item_id, "org": current["organization_id"]},
        ).mappings().first()
        if not item:
            raise HTTPException(404, {"code": "not_found", "message": "That page is not available.", "retryable": False})
        if item["slug"] in _REQUIRED_SLUGS:
            raise HTTPException(403, {"code": "guardrail", "message": "That required public path cannot be removed.", "retryable": False})
        if item["version"] != body.expected_version:
            raise HTTPException(409, {"code": "stale_version", "message": "This content changed. Reload it and try again.", "retryable": True})
        connection.execute(
            text(
                """
                UPDATE content_publications
                SET superseded_at = now()
                WHERE organization_id = :org AND slug = :slug AND superseded_at IS NULL
                """
            ),
            {"org": current["organization_id"], "slug": item["slug"]},
        )
        updated = connection.execute(
            text(
                """
                UPDATE content_items
                SET status = 'unpublished', version = version + 1
                WHERE id = :id AND organization_id = :org AND version = :version
                RETURNING version
                """
            ),
            {"id": item_id, "org": current["organization_id"], "version": item["version"]},
        ).scalar()
    _PUBLIC_CACHE.pop(item["slug"], None)
    return {"unpublished": True, "version": updated, "synthetic": True}


@router.post("/content/{item_id}/rollback")
def rollback_item(item_id: UUID, body: RollbackBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        item = connection.execute(
            text("SELECT id, slug, version, risk_class FROM content_items WHERE id = :id AND organization_id = :org"),
            {"id": item_id, "org": current["organization_id"]},
        ).mappings().first()
        if not item:
            raise HTTPException(404, {"code": "not_found", "message": "That page is not available.", "retryable": False})
        if item["version"] != body.expected_version:
            raise HTTPException(409, {"code": "stale_version", "message": "This content changed. Reload it and try again.", "retryable": True})
        source = connection.execute(
            text(
                """
                SELECT id, version, blocks FROM content_revisions
                WHERE id = :id AND item_id = :item AND organization_id = :org AND version < :version
                """
            ),
            {"id": body.revision_id, "item": item_id, "org": current["organization_id"], "version": item["version"]},
        ).mappings().first()
        if not source:
            raise HTTPException(404, {"code": "not_found", "message": "That revision cannot be restored.", "retryable": False})
        revision_id = uuid4()
        connection.execute(
            text(
                """
                INSERT INTO content_revisions (
                  organization_id, id, item_id, version, blocks, author_id, reason
                ) VALUES (:org, :id, :item, :version, CAST(:blocks AS jsonb), :author, :reason)
                """
            ),
            {
                "org": current["organization_id"],
                "id": revision_id,
                "item": item_id,
                "version": item["version"],
                "blocks": json.dumps(source["blocks"]),
                "author": current["id"],
                "reason": body.reason,
            },
        )
        connection.execute(
            text(
                """
                UPDATE content_publications SET superseded_at = now()
                WHERE organization_id = :org AND slug = :slug AND superseded_at IS NULL
                """
            ),
            {"org": current["organization_id"], "slug": item["slug"]},
        )
        try:
            connection.execute(
                text(
                    """
                    INSERT INTO content_publications (
                      organization_id, id, item_id, revision_id, slug, snapshot, actor_id
                    ) VALUES (:org, :id, :item, :revision, :slug, CAST(:snapshot AS jsonb), :actor)
                    """
                ),
                {
                    "org": current["organization_id"],
                    "id": uuid4(),
                    "item": item_id,
                    "revision": revision_id,
                    "slug": item["slug"],
                    "snapshot": json.dumps(source["blocks"]),
                    "actor": current["id"],
                },
            )
        except Exception as exc:
            raise HTTPException(403, {"code": "denied", "message": "This revision cannot be published.", "retryable": False}) from exc
        updated = _mark_published(connection, current["organization_id"], item_id, item["version"], item["slug"], "content.rolled_back")
    _PUBLIC_CACHE.pop(item["slug"], None)
    return {"rolled_back": True, "revision_id": str(revision_id), "version": updated, "synthetic": True}


@router.post("/content/{item_id}/schedule", status_code=202)
def schedule_item(item_id: UUID, body: ScheduleBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    if body.action not in {"publish", "expire"} or body.time_zone.count("/") != 1:
        raise HTTPException(400, {"code": "rejected", "message": "That schedule cannot be saved.", "retryable": False})
    run_at = _when(body.run_at)
    job_id = uuid4()
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        allowed = connection.execute(text("SELECT perchpoint.has_capability('content.schedule')")).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This session cannot schedule content.", "retryable": False})
        item = connection.execute(
            text("SELECT version FROM content_items WHERE id = :id AND organization_id = :org"),
            {"id": item_id, "org": current["organization_id"]},
        ).mappings().first()
        if not item or item["version"] != body.expected_version:
            raise HTTPException(409, {"code": "stale_version", "message": "This content changed. Reload it and try again.", "retryable": True})
        connection.execute(
            text(
                """
                INSERT INTO content_jobs (
                  organization_id, id, item_id, action, run_at, time_zone, status, initiator_id
                ) VALUES (:org, :id, :item, :action, :run_at, :zone, 'pending', :actor)
                """
            ),
            {
                "org": current["organization_id"],
                "id": job_id,
                "item": item_id,
                "action": body.action,
                "run_at": run_at,
                "zone": body.time_zone,
                "actor": current["id"],
            },
        )
        connection.execute(
            text(
                """
                UPDATE content_items
                SET status = 'scheduled', scheduled_for = :run_at, schedule_zone = :zone
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"id": item_id, "org": current["organization_id"], "run_at": run_at, "zone": body.time_zone},
        )
    return {"scheduled": True, "id": str(job_id), "synthetic": True}


@router.post("/content/jobs/run")
def run_due_jobs(current=Depends(actor), current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        allowed = connection.execute(text("SELECT perchpoint.has_capability('content.schedule')")).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This session cannot run publication jobs.", "retryable": False})
        jobs = connection.execute(
            text(
                """
                SELECT id, item_id, action, initiator_id
                FROM content_jobs
                WHERE organization_id = :org AND status = 'pending' AND run_at <= now()
                ORDER BY run_at
                """
            ),
            {"org": current["organization_id"]},
        ).mappings().all()
    results = []
    for job in jobs:
        results.append(_execute_job(current_settings, current["organization_id"], current["id"], job))
    return {"jobs": results, "synthetic": True}


def _execute_job(current_settings: Settings, organization_id, runner_id, job) -> dict:
    status = "failed"
    error: str | None = "failed"
    slug = None
    try:
        slug = _apply_due_job(current_settings, organization_id, job)
        status = "succeeded"
        error = None
    except Exception as exc:
        message = str(getattr(exc, "orig", exc))
        if "authority_recheck_failed" in message or "elevated_approval_required" in message or "self_approval" in message:
            error = "authority_recheck_failed"
    with runtime_transaction(current_settings, runner_id, organization_id, uuid4()) as connection:
        connection.execute(
            text(
                """
                UPDATE content_jobs
                SET status = :status, attempts = attempts + 1, last_error = :error, finished_at = now()
                WHERE id = :id AND organization_id = :org
                """
            ),
            {"status": status, "error": error, "id": job["id"], "org": organization_id},
        )
    if slug:
        _PUBLIC_CACHE.pop(slug, None)
    return {"id": str(job["id"]), "status": status, "error": error, "synthetic": True}


def _apply_due_job(current_settings: Settings, organization_id, job) -> str:
    initiator = job["initiator_id"]
    with runtime_transaction(current_settings, initiator, organization_id, uuid4()) as connection:
        item = connection.execute(
            text("SELECT id, slug, version, risk_class, status FROM content_items WHERE id = :id AND organization_id = :org"),
            {"id": job["item_id"], "org": organization_id},
        ).mappings().first()
        if not item:
            raise RuntimeError("authority_recheck_failed")
        if item["slug"] in _REQUIRED_SLUGS and job["action"] == "expire":
            raise RuntimeError("authority_recheck_failed")
        capability = "content.approve" if item["risk_class"] == "elevated" and job["action"] == "publish" else "content.publish"
        allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
        if not allowed:
            raise RuntimeError("authority_recheck_failed")
        if job["action"] == "publish":
            revision = connection.execute(
                text(
                    """
                    SELECT id, blocks FROM content_revisions
                    WHERE item_id = :item AND organization_id = :org AND version = :version
                    """
                ),
                {"item": item["id"], "org": organization_id, "version": item["version"]},
            ).mappings().first()
            if not revision:
                raise RuntimeError("failed")
            connection.execute(
                text("UPDATE content_publications SET superseded_at = now() WHERE organization_id = :org AND slug = :slug AND superseded_at IS NULL"),
                {"org": organization_id, "slug": item["slug"]},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO content_publications (
                      organization_id, id, item_id, revision_id, slug, snapshot, actor_id
                    ) VALUES (:org, :id, :item, :revision, :slug, CAST(:snapshot AS jsonb), :actor)
                    """
                ),
                {
                    "org": organization_id,
                    "id": uuid4(),
                    "item": item["id"],
                    "revision": revision["id"],
                    "slug": item["slug"],
                    "snapshot": json.dumps(revision["blocks"]),
                    "actor": initiator,
                },
            )
            _mark_published(connection, organization_id, item["id"], item["version"], item["slug"], "content.published")
        else:
            connection.execute(
                text("UPDATE content_publications SET superseded_at = now() WHERE organization_id = :org AND slug = :slug AND superseded_at IS NULL"),
                {"org": organization_id, "slug": item["slug"]},
            )
            connection.execute(
                text(
                    """
                    UPDATE content_items
                    SET status = 'expired', version = version + 1, scheduled_for = NULL
                    WHERE id = :id AND organization_id = :org AND version = :version
                    """
                ),
                {"id": item["id"], "org": organization_id, "version": item["version"]},
            )
        return item["slug"]


@router.get("/content/preview/{slug}")
def preview_slug(slug: str, response: Response, current=Depends(actor), current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        allowed = connection.execute(text("SELECT perchpoint.has_capability('content.preview')")).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This session cannot preview content.", "retryable": False})
        row = connection.execute(
            text(
                """
                SELECT item.slug, item.status, revision.blocks
                FROM content_items item
                JOIN content_revisions revision
                  ON revision.organization_id = item.organization_id
                 AND revision.item_id = item.id
                WHERE item.organization_id = :org AND item.slug = :slug
                ORDER BY revision.version DESC
                LIMIT 1
                """
            ),
            {"org": current["organization_id"], "slug": slug},
        ).mappings().first()
    if not row:
        raise HTTPException(404, {"code": "not_found", "message": "That draft is not available.", "retryable": False})
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return {"slug": row["slug"], "status": row["status"], "snapshot": row["blocks"], "noindex": True, "synthetic": True}


@router.get("/content/conversions")
def conversions(current=Depends(actor), current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        allowed = connection.execute(text("SELECT perchpoint.has_capability('content.report')")).scalar()
        if not allowed:
            raise HTTPException(403, {"code": "denied", "message": "This session cannot read conversions.", "retryable": False})
        rows = connection.execute(
            text(
                """
                SELECT intent, count(*) AS total
                FROM public_submissions
                WHERE organization_id = :org
                GROUP BY intent
                ORDER BY intent
                """
            ),
            {"org": current["organization_id"]},
        ).mappings().all()
    return {"definitions": "accepted public submissions by intent", "freshness": "transactional", "totals": [_jsonable(row) for row in rows], "synthetic": True}


def _jsonable(row) -> dict:
    item = dict(row)
    for key, value in item.items():
        if isinstance(value, UUID):
            item[key] = str(value)
        elif hasattr(value, "isoformat"):
            item[key] = value.isoformat()
    return item


def _require_content(connection, capability: str, message: str) -> None:
    allowed = connection.execute(text("SELECT perchpoint.has_capability(:capability)"), {"capability": capability}).scalar()
    if not allowed:
        raise HTTPException(403, {"code": "denied", "message": message, "retryable": False})


@router.get("/content/items")
def list_content(current=Depends(actor), current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        _require_content(connection, "content.read", "This session cannot read content.")
        rows = connection.execute(
            text(
                """
                SELECT id, slug, kind, risk_class, status, version
                FROM content_items
                WHERE organization_id = :org
                ORDER BY slug
                """
            ),
            {"org": current["organization_id"]},
        ).mappings().all()
    return {"items": [_jsonable(row) for row in rows], "synthetic": True}


@router.get("/content/jobs")
def list_jobs(current=Depends(actor), current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        _require_content(connection, "content.read", "This session cannot read publication jobs.")
        rows = connection.execute(
            text(
                """
                SELECT id, item_id, action, status, last_error, run_at, time_zone, attempts
                FROM content_jobs
                WHERE organization_id = :org
                ORDER BY run_at DESC
                """
            ),
            {"org": current["organization_id"]},
        ).mappings().all()
    return {"jobs": [_jsonable(row) for row in rows], "synthetic": True}


@router.get("/content/redirects")
def list_redirects(current=Depends(actor), current_settings: Settings = Depends(settings)):
    with runtime_transaction(current_settings, current["id"], current["organization_id"], uuid4()) as connection:
        _require_content(connection, "content.read", "This session cannot read redirects.")
        rows = connection.execute(
            text(
                """
                SELECT id, source_path, destination_path, status_code
                FROM content_redirects
                WHERE organization_id = :org
                ORDER BY source_path
                """
            ),
            {"org": current["organization_id"]},
        ).mappings().all()
    return {"redirects": [_jsonable(row) for row in rows], "synthetic": True}

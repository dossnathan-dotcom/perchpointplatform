"""Public discovery and staff listing-health routes. No external syndication."""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, HTTPException, Response
from pydantic import BaseModel, Field

from .commands import CommandError
from .phase9_discovery import (
    OWNED_TARGETS,
    approve_ranking,
    claim_job,
    complete_job,
    health,
    marketed_interval,
    project_listing,
    public_listing,
    reconcile,
    record_event,
    search_public,
    sitemap,
    withdraw_listing,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class ProjectBody(BaseModel):
    snapshot_id: UUID
    bedrooms: int | None = None
    bathrooms: float | None = None
    area_sqft: int | None = None
    neighborhood: str = ""
    postal_code: str = ""
    pet_policy: str = ""
    amenities: list[str] = Field(default_factory=list)
    accessibility_features: list[str] = Field(default_factory=list)
    verification_on: str = ""
    latitude: float | None = None
    longitude: float | None = None
    available_on: str = ""
    target: str = ""
    idempotency_key: str


class WithdrawBody(BaseModel):
    public_slug: str
    idempotency_key: str


class RankingBody(BaseModel):
    version: int = Field(ge=1)
    reason: str
    effective_on: str
    idempotency_key: str


class ReconcileBody(BaseModel):
    idempotency_key: str


class EventBody(BaseModel):
    event_name: str
    listing_slug: str = ""
    session_ref: str = ""
    source: str = ""
    medium: str = ""
    campaign: str = ""
    classification: str = ""
    idempotency_key: str


class ClaimBody(BaseModel):
    idempotency_key: str


class CompleteBody(BaseModel):
    operation_id: UUID
    expected_version: int
    terminal: bool = False
    idempotency_key: str


def _call(action):
    try:
        return action()
    except CommandError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


@router.get("/public/discovery/search")
def discovery_search(
    response: Response,
    use_code: str = "",
    city: str = "",
    postal_code: str = "",
    max_amount: str = "",
    min_bedrooms: str = "",
    max_bedrooms: str = "",
    min_bathrooms: str = "",
    min_area: str = "",
    neighborhood: str = "",
    pet_policy: str = "",
    amenity: str = "",
    accessibility: str = "",
    move_in: str = "",
    origin_lat: str = "",
    origin_lon: str = "",
    radius_km: str = "",
    query: str = "",
    sort: str = "",
    limit: int = 20,
    offset: int = 0,
    current_settings: Settings = Depends(settings),
):
    response.headers["cache-control"] = "public, max-age=60"
    response.headers["x-robots-tag"] = "index, follow"
    return _call(lambda: search_public(current_settings, {
        "use_code": use_code,
        "city": city,
        "postal_code": postal_code,
        "max_amount": max_amount,
        "min_bedrooms": min_bedrooms,
        "max_bedrooms": max_bedrooms,
        "min_bathrooms": min_bathrooms,
        "min_area": min_area,
        "neighborhood": neighborhood,
        "pet_policy": pet_policy,
        "amenity": amenity,
        "accessibility": accessibility,
        "move_in": move_in,
        "origin_lat": origin_lat,
        "origin_lon": origin_lon,
        "radius_km": radius_km,
        "query": query,
        "sort": sort,
        "limit": limit,
        "offset": offset,
    }))


@router.get("/public/discovery/listings/{slug}")
def discovery_listing(slug: str, response: Response, current_settings: Settings = Depends(settings)):
    payload = public_listing(current_settings, slug)
    if not payload:
        response.headers["x-robots-tag"] = "noindex"
        raise HTTPException(410, {"code": "withdrawn", "message": "This listing is no longer offered.", "retryable": False})
    response.headers["cache-control"] = "public, max-age=60"
    response.headers["x-robots-tag"] = "index, follow"
    return payload


@router.get("/public/discovery/sitemap.xml")
def discovery_sitemap(current_settings: Settings = Depends(settings)):
    return sitemap(current_settings)


@router.get("/public/discovery/compare")
def discovery_compare(slugs: str = "", current_settings: Settings = Depends(settings)):
    chosen = [item for item in slugs.split(",") if item][:3]
    records = []
    for slug in chosen:
        payload = public_listing(current_settings, slug)
        if payload:
            records.append(payload)
    return {"records": records, "limit": 3, "synthetic": True}


@router.post("/public/discovery/events", status_code=201)
def discovery_event(body: EventBody, sec_gpc: str | None = Header(default=None, alias="sec-gpc"), current_settings: Settings = Depends(settings)):
    return _call(lambda: record_event(current_settings, body.model_dump(), gpc=sec_gpc == "1"))


@router.post("/discovery/project", status_code=201)
def discovery_project(body: ProjectBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: project_listing(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/discovery/withdraw")
def discovery_withdraw(body: WithdrawBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: withdraw_listing(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/discovery/ranking", status_code=201)
def discovery_ranking(body: RankingBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: approve_ranking(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/discovery/reconcile")
def discovery_reconcile(body: ReconcileBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: reconcile(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/discovery/jobs/claim")
def discovery_claim(body: ClaimBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: claim_job(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/discovery/jobs/complete")
def discovery_complete(body: CompleteBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: complete_job(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.get("/discovery/marketed")
def discovery_marketed(public_slug: str, current=Depends(actor), current_settings: Settings = Depends(settings)):
    return _call(lambda: marketed_interval(current_settings, current["id"], current["organization_id"], public_slug))


@router.get("/discovery/health")
def discovery_health(current=Depends(actor), current_settings: Settings = Depends(settings)):
    return health(current_settings, current["id"], current["organization_id"])


@router.get("/discovery/targets")
def discovery_targets(current=Depends(actor)):
    return {"targets": list(OWNED_TARGETS), "external_syndication": "disabled"}

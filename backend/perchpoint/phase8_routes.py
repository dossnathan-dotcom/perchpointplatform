"""Authenticated property administration and the public listing snapshot."""
from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field

from .commands import CommandError
from .phase8_portfolio import (
    apply_asking_price,
    archive_property,
    bulk_apply,
    bulk_dry_run,
    inventory,
    place_hold,
    public_snapshot,
    publish_snapshot,
    record_fee,
    register_media,
    release_due_holds,
    set_availability,
    set_readiness,
    unpublish_snapshot,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class ReadinessBody(BaseModel):
    space_id: UUID
    readiness: str
    reason: str = Field(min_length=8, max_length=240)
    idempotency_key: str = Field(min_length=8, max_length=80)


class AvailabilityBody(BaseModel):
    space_id: UUID
    availability: str
    effective_on: str
    confidence: str
    source: str
    reason: str = Field(min_length=8, max_length=240)
    idempotency_key: str = Field(min_length=8, max_length=80)


class PriceBody(BaseModel):
    space_id: UUID
    amount_minor: int = Field(ge=0, le=100_000_000)
    effective_on: str
    reason: str = Field(min_length=8, max_length=240)
    currency: str = "USD"
    period: str = "monthly"
    idempotency_key: str = Field(min_length=8, max_length=80)


class FeeBody(BaseModel):
    space_id: UUID
    code: str
    label: str
    amount_minor: int = Field(ge=0)
    required: bool
    recurring: bool
    refundable: bool
    effective_on: str
    currency: str = "USD"
    idempotency_key: str


class HoldBody(BaseModel):
    space_id: UUID
    reason: str
    holder_label: str
    expires_at: str
    idempotency_key: str


class MediaBody(BaseModel):
    space_id: UUID
    content: str
    signature: str
    declared_mime: str
    alt_text: str = ""
    rights_state: str = "unknown"
    sort_order: int = 0
    idempotency_key: str


class PublishBody(BaseModel):
    listing_id: UUID
    expected_version: int = Field(ge=1)
    public_slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    description: str = "EXAMPLE ONLY. Synthetic listing facts."
    idempotency_key: str


class UnpublishBody(BaseModel):
    public_slug: str
    idempotency_key: str


class ArchiveBody(BaseModel):
    property_id: UUID
    expected_version: int = Field(ge=1)
    idempotency_key: str


class BulkBody(BaseModel):
    space_ids: list[str]
    amount_minor: int = Field(ge=0)
    effective_on: str = "2026-12-01"
    reason: str = "Synthetic bulk asking rent."
    idempotency_key: str = ""


def _call(operation):
    try:
        return operation()
    except CommandError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


@router.get("/portfolio/inventory")
def portfolio_inventory(current=Depends(actor), current_settings: Settings = Depends(settings)):
    return inventory(current_settings, current["id"], current["organization_id"])


@router.post("/portfolio/readiness", status_code=201)
def portfolio_readiness(body: ReadinessBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: set_readiness(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/availability", status_code=201)
def portfolio_availability(body: AvailabilityBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: set_availability(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/prices", status_code=201)
def portfolio_price(body: PriceBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: apply_asking_price(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/fees", status_code=201)
def portfolio_fee(body: FeeBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: record_fee(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/holds", status_code=201)
def portfolio_hold(body: HoldBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: place_hold(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/holds/release-due")
def portfolio_release(current=Depends(actor), current_settings: Settings = Depends(settings)):
    return release_due_holds(current_settings, current["id"], current["organization_id"])


@router.post("/portfolio/media", status_code=201)
def portfolio_media(body: MediaBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: register_media(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/snapshots", status_code=201)
def portfolio_publish(body: PublishBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: publish_snapshot(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/snapshots/unpublish")
def portfolio_unpublish(body: UnpublishBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: unpublish_snapshot(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/archive")
def portfolio_archive(body: ArchiveBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: archive_property(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/portfolio/bulk/dry-run")
def portfolio_bulk(body: BulkBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    return bulk_dry_run(current_settings, current["id"], current["organization_id"], body.model_dump())


@router.post("/portfolio/bulk/apply")
def portfolio_bulk_apply(body: BulkBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key") or _key_fallback()
    return _call(lambda: bulk_apply(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


def _key_fallback() -> str:
    return "bulk-" + uuid4().hex


@router.get("/public/listing-snapshots/{slug}")
def public_listing_snapshot(slug: str, response: Response, current_settings: Settings = Depends(settings)):
    payload = public_snapshot(current_settings, slug)
    if not payload:
        raise HTTPException(404, {"code": "not_found", "message": "This listing is not public.", "retryable": False})
    response.headers["cache-control"] = "public, max-age=60"
    return payload

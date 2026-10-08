"""Public leasing intake and staff CRM commands. Showings and applications stay out of this router."""
from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from .commands import CommandError
from .phase10_crm import (
    add_note,
    add_tag,
    attempt_contact,
    capture_public,
    claim,
    detail,
    merge_prospects,
    metrics,
    owner_summary,
    queue,
    record_staff,
    suppress_contact,
    transition,
    unmerge_prospect,
)
from .routes import actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class PublicInquiry(BaseModel):
    name: str = ""
    email: str = ""
    phone: str = ""
    message: str = ""
    public_slug: str = ""
    slugs: str = ""
    disclosure: bool = False
    honeypot: str = ""
    marketing_opt_in: bool = False
    fail_delivery: bool = False
    search_ref: str = ""
    position: str = ""
    first_touch: str = ""
    last_touch: str = ""
    idempotency_key: str = Field(min_length=8, max_length=128)
    organization_id: str | None = None
    snapshot_id: str | None = None
    prospect_id: str | None = None
    lead_score: str | None = None
    tenant_quality: str | None = None
    attachment: str | None = None


class StaffInquiry(BaseModel):
    name: str
    email: str
    source: str
    received_at: str
    idempotency_key: str


class ReceiptBody(BaseModel):
    receipt: str
    expected_version: int
    stage: str = ""
    reason: str = ""
    idempotency_key: str


class NoteBody(BaseModel):
    receipt: str
    body: str
    idempotency_key: str


class TagBody(BaseModel):
    code: str
    idempotency_key: str


class AttemptBody(BaseModel):
    receipt: str
    outcome: str
    summary: str
    idempotency_key: str


class SuppressBody(BaseModel):
    email: str
    idempotency_key: str


class MergeBody(BaseModel):
    survivor_id: str
    alias_id: str
    expected_version: int
    reason: str
    dry_run: bool = False
    idempotency_key: str


class UnmergeBody(BaseModel):
    alias_id: str
    idempotency_key: str


def _call(action):
    try:
        return action()
    except CommandError as exc:
        raise HTTPException(exc.status, {"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


@router.post("/public/leasing/inquiries", status_code=201)
def public_inquiry(body: PublicInquiry, sec_gpc: str | None = Header(default=None, alias="sec-gpc"), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    payload.pop("idempotency_key")
    for field in ("organization_id", "snapshot_id", "prospect_id", "lead_score", "tenant_quality", "attachment"):
        if payload.get(field) is None:
            payload.pop(field, None)
    return _call(lambda: capture_public(current_settings, {**payload, "idempotency_key": body.idempotency_key}, gpc=sec_gpc == "1"))


@router.post("/leasing/inquiries", status_code=201)
def staff_inquiry(body: StaffInquiry, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: record_staff(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.get("/leasing/queue")
def leasing_queue(receipt: str = "", current=Depends(actor), current_settings: Settings = Depends(settings)):
    return _call(lambda: queue(current_settings, current["id"], current["organization_id"], receipt or None))


@router.get("/leasing/inquiries/{receipt}")
def leasing_detail(receipt: str, current=Depends(actor), current_settings: Settings = Depends(settings)):
    return _call(lambda: detail(current_settings, current["id"], current["organization_id"], receipt))


@router.post("/leasing/transitions")
def leasing_transition(body: ReceiptBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: transition(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/leasing/claims")
def leasing_claim(body: ReceiptBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: claim(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/leasing/notes", status_code=201)
def leasing_note(body: NoteBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: add_note(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/leasing/tags", status_code=201)
def leasing_tag(body: TagBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: add_tag(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/leasing/attempts", status_code=201)
def leasing_attempt(body: AttemptBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: attempt_contact(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/leasing/suppressions")
def leasing_suppress(body: SuppressBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: suppress_contact(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/leasing/merges")
def leasing_merge(body: MergeBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: merge_prospects(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.post("/leasing/unmerges")
def leasing_unmerge(body: UnmergeBody, current=Depends(actor), current_settings: Settings = Depends(settings)):
    payload = body.model_dump(mode="json")
    key = payload.pop("idempotency_key")
    return _call(lambda: unmerge_prospect(current_settings, current["id"], current["organization_id"], payload, key, uuid4()))


@router.get("/leasing/metrics")
def leasing_metrics(current=Depends(actor), current_settings: Settings = Depends(settings)):
    return _call(lambda: metrics(current_settings, current["id"], current["organization_id"]))


@router.get("/leasing/owner-summary")
def leasing_owner(current=Depends(actor), current_settings: Settings = Depends(settings)):
    return _call(lambda: owner_summary(current_settings, current["id"], current["organization_id"]))

"""Phase 21 call routes. Provider events are signed. No recording is accepted."""
import os

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .phase21_calls import (
    acknowledge,
    add_note,
    apply_provider_event,
    desk,
    link_case,
    record_manual,
    recording_posture,
    review_caller,
    save_route,
    schedule_callback,
)
from .phase6_identity import resolve
from .routes import COOKIE, _require_csrf, actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class ManualBody(BaseModel):
    description: str
    caller_hint: str = ""
    duration_source: str = "unknown"
    duration_seconds: int | None = None
    idempotency_key: str = Field(min_length=8)


class RouteBody(BaseModel):
    edges: list[list[str]]
    account_sid: str = "AC-local-synthetic"


class ReferenceBody(BaseModel):
    reference: str
    body: str = ""
    case_reference: str = ""
    due_at: str | None = None
    reason: str = ""
    caller_status: str = ""


def _call(action):
    try:
        return action()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "That call was not accepted.", "retryable": False}) from exc
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


def _browser(request: Request, current: Settings) -> None:
    session = resolve(current, request.cookies.get(COOKIE))
    if session and session.get("status") == "active":
        _require_csrf(request, session)


@router.get("/calls/desk")
def read_desk(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: desk(current, current_actor["id"], current_actor["organization_id"]))


@router.get("/calls/posture")
def read_posture(current_actor=Depends(actor)) -> dict:
    del current_actor
    return recording_posture()


@router.post("/calls/routing")
def write_route(body: RouteBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: save_route(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/calls/manual")
def write_manual(body: ManualBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: record_manual(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/calls/acknowledge")
def write_ack(body: ReferenceBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: acknowledge(current, current_actor["id"], current_actor["organization_id"], body.reference))


@router.post("/calls/notes")
def write_note(body: ReferenceBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: add_note(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/calls/links")
def write_link(body: ReferenceBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: link_case(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/calls/callbacks")
def write_callback(body: ReferenceBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: schedule_callback(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/calls/caller")
def write_caller(body: ReferenceBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: review_caller(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/calls/provider-events")
async def provider_event(request: Request, current: Settings = Depends(settings)) -> dict:
    form = await request.form()
    params = {key: str(value) for key, value in form.items()}
    signature = request.headers.get("x-twilio-signature", "")
    override = request.headers.get("x-perchpoint-signature-url")
    local = os.environ.get("PHASE3_ENVIRONMENT", "local") in {"local", "test"}
    url = str(override if local and override else request.url)
    return _call(lambda: apply_provider_event(current, url, params, signature))

"""Phase 19 reconciliation routes. A bank row is not a payment. No money moves."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .phase19_reconciliation import acknowledge, briefing, claim, import_lines, issue_close, match_line, packet, prepare_close, preview_lines, queue
from .phase6_identity import resolve
from .routes import COOKIE, _require_csrf, actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class LineBody(BaseModel):
    external_id: str
    kind: str
    amount_minor: int | str
    status: str
    currency_code: str = "USD"
    link_reference: str | None = None


class ImportBody(BaseModel):
    source_reference: str
    source_kind: str = "bank"
    refresh_state: str = "current"
    lines: list[LineBody]
    idempotency_key: str = Field(min_length=8)


class PreviewBody(BaseModel):
    lines: list[LineBody]


class MatchBody(BaseModel):
    line_reference: str
    target_reference: str
    amount_minor: int | str
    idempotency_key: str = Field(min_length=8)


class ClaimBody(BaseModel):
    line_reference: str
    version: int
    idempotency_key: str = Field(min_length=8)


class SnapshotBody(BaseModel):
    snapshot_reference: str
    idempotency_key: str = Field(min_length=8)


class IssueBody(BaseModel):
    close_reference: str
    idempotency_key: str = Field(min_length=8)


def _call(action):
    try:
        return action()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "That reconciliation request was not accepted.", "retryable": False}) from exc
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


def _browser(request: Request, current: Settings) -> None:
    session = resolve(current, request.cookies.get(COOKIE))
    if session and session.get("status") == "active":
        _require_csrf(request, session)


@router.post("/payments/reconciliation/preview")
def create_preview(body: PreviewBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    del current_actor
    _browser(request, current)
    return _call(lambda: preview_lines([line.model_dump() for line in body.lines]))


@router.post("/payments/reconciliation/imports")
def create_import(body: ImportBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: import_lines(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/reconciliation/matches")
def create_match(body: MatchBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: match_line(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.get("/payments/reconciliation/queue")
def read_queue(q: str | None = None, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: queue(current, current_actor["id"], current_actor["organization_id"], q))


@router.post("/payments/reconciliation/claims")
def create_claim(body: ClaimBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: claim(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.get("/payments/reconciliation/briefing")
def read_briefing(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: briefing(current, current_actor["id"], current_actor["organization_id"]))


@router.post("/payments/reconciliation/acknowledgements")
def create_acknowledgement(body: SnapshotBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: acknowledge(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/reconciliation/closes")
def create_close(body: SnapshotBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: prepare_close(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/reconciliation/closes/issue")
def create_issue(body: IssueBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: issue_close(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.get("/payments/reconciliation/packet")
def read_packet(reference: str, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: packet(current, current_actor["id"], current_actor["organization_id"], reference))

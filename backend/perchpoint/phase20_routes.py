"""Phase 20 maintenance routes. No money moves."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .phase20_maintenance import (
    acknowledge,
    add_evidence,
    add_manual_time,
    add_need,
    add_note,
    add_notice,
    briefing,
    change_severity,
    check_compatibility,
    check_in,
    decide,
    detail,
    intake,
    jobs,
    link_cases,
    mine,
    plan_visit,
    propose_assignment,
    queue,
    read_locations,
    record_access,
    record_fulfillment,
    respond_assignment,
    review_completion,
    start_time,
    withdraw,
    stop_time,
    submit_completion,
    correct_time,
)
from .phase6_identity import resolve
from .routes import COOKIE, _require_csrf, actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class IntakeBody(BaseModel):
    description: str
    place_label: str
    place_kind: str = "unit"
    source: str = "resident"
    urgency: dict = Field(default_factory=dict)
    household_label: str | None = None
    reported_at: str | None = None
    resident_actor: str | None = None
    synthetic_fail_first_delivery: bool = False
    idempotency_key: str = Field(min_length=8)


class ReferenceBody(BaseModel):
    reference: str
    version: int | None = None
    idempotency_key: str | None = None


def _call(action):
    try:
        return action()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "That maintenance request was not accepted.", "retryable": False}) from exc
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


def _browser(request: Request, current: Settings) -> None:
    session = resolve(current, request.cookies.get(COOKIE))
    if session and session.get("status") == "active":
        _require_csrf(request, session)


@router.post("/maintenance/intake")
def create_intake(body: IntakeBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: intake(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.get("/maintenance/mine")
def read_mine(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: mine(current, current_actor["id"], current_actor["organization_id"]))


@router.get("/maintenance/mine/{reference}")
def read_my_detail(reference: str, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: detail(current, current_actor["id"], current_actor["organization_id"], reference))


@router.get("/maintenance/desk/queue")
def read_queue(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: queue(current, current_actor["id"], current_actor["organization_id"]))


@router.get("/maintenance/briefing")
def read_briefing(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: briefing(current, current_actor["id"], current_actor["organization_id"]))


@router.get("/maintenance/desk/{reference}")
def read_detail(reference: str, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: detail(current, current_actor["id"], current_actor["organization_id"], reference))


@router.post("/maintenance/desk/acknowledge")
def create_acknowledgement(body: ReferenceBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: acknowledge(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/maintenance/desk/assignments")
def create_assignment(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: propose_assignment(current, current_actor["id"], current_actor["organization_id"], body))


@router.get("/maintenance/jobs")
def read_jobs(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: jobs(current, current_actor["id"], current_actor["organization_id"]))


@router.post("/maintenance/jobs/assignments")
def create_assignment_response(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: respond_assignment(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/jobs/needs")
def create_need(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: add_need(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/decisions")
def create_decision(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: decide(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/fulfillment")
def create_fulfillment(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: record_fulfillment(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/jobs/compatibility")
def create_compatibility(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: check_compatibility(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/jobs/time/start")
def create_time_start(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: start_time(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/jobs/time/stop")
def create_time_stop(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: stop_time(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/jobs/time/manual")
def create_manual_time(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: add_manual_time(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/jobs/time/corrections")
def create_worker_time_correction(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: correct_time(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/time/corrections")
def create_time_correction(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: correct_time(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/jobs/location")
def create_location(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: check_in(current, current_actor["id"], current_actor["organization_id"], body))


@router.get("/maintenance/jobs/location/{reference}")
def read_location(reference: str, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: read_locations(current, current_actor["id"], current_actor["organization_id"], reference))


@router.post("/maintenance/jobs/evidence")
def create_evidence(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: add_evidence(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/jobs/completion")
def create_completion(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: submit_completion(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/reviews")
def create_review(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: review_completion(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/notices")
def create_notice(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: add_notice(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/notes")
def create_note(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: add_note(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/mine/notes")
def create_resident_note(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: add_note(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/links")
def create_link(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: link_cases(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/severity")
def create_severity(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: change_severity(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/visits")
def create_visit(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: plan_visit(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/mine/withdraw")
def create_withdrawal(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: withdraw(current, current_actor["id"], current_actor["organization_id"], body))


@router.post("/maintenance/desk/access")
def create_access(body: dict, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: record_access(current, current_actor["id"], current_actor["organization_id"], body))

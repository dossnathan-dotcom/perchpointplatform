"""Phase 18 assistance routes. A report is not a payment. No money moves."""
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.exc import IntegrityError

from .commands import CommandError
from .phase18_assistance import (
    apply_batch,
    apply_receipt,
    configuration,
    resolve_receipt,
    household_directory,
    household_view,
    ingest_receipt,
    owner_measures,
    queue,
    record_batch,
    complete_required_return,
    record_required_return,
    record_determination,
    report_transfer,
    transfer_instructions,
)
from .phase6_identity import resolve
from .routes import COOKIE, _require_csrf, actor, settings
from .settings import Settings

router = APIRouter(prefix="/api/v2")


class DeterminationBody(BaseModel):
    tenancy_code: str
    account_reference: str | None = None
    program_kind: str = "hcv"
    agency_name: str = "Synthetic housing agency"
    household_label: str | None = None
    resident_email: str | None = None
    service_period: str
    rent_to_owner_minor: int
    resident_minor: int
    agency_minor: int
    utility_allowance_minor: int = 0
    utility_reimbursement_minor: int = 0
    idempotency_key: str = Field(min_length=8)


class ReceiptBody(BaseModel):
    source: str
    external_id: str
    method: str
    amount_minor: int
    tenancy_code: str | None = None
    service_period: str | None = None
    purpose: str | None = None
    stripe_kind: str | None = None
    idempotency_key: str = Field(min_length=8)


class ApplyBody(BaseModel):
    receipt_reference: str
    idempotency_key: str = Field(min_length=8)


class ResolveBody(BaseModel):
    receipt_reference: str
    tenancy_code: str
    service_period: str
    idempotency_key: str = Field(min_length=8)


class BatchRow(BaseModel):
    tenancy_code: str | None = None
    service_period: str | None = None
    gross_minor: int


class BatchBody(BaseModel):
    external_id: str
    gross_minor: int
    recoupment_minor: int = 0
    adjustment_minor: int = 0
    net_minor: int
    cash_external_id: str | None = None
    rows: list[BatchRow]
    idempotency_key: str = Field(min_length=8)


class BatchApplyBody(BaseModel):
    batch_reference: str
    idempotency_key: str = Field(min_length=8)


class ReturnBody(BaseModel):
    exception_reference: str
    recipient: str
    idempotency_key: str = Field(min_length=8)
    paid: bool | None = None
    state: str | None = None
    mandatory: bool | None = None


class ReturnCompletionBody(BaseModel):
    return_reference: str
    evidence_key: str
    idempotency_key: str = Field(min_length=8)
    paid: bool | None = None
    mandatory: bool | None = None


class ReportBody(BaseModel):
    tenancy_code: str
    amount_minor: int
    reference_text: str
    explanation: str
    idempotency_key: str = Field(min_length=8)


class InstructionBody(BaseModel):
    tenancy_code: str


def _call(action):
    try:
        return action()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail={"code": "conflict", "message": "That assistance request was not accepted.", "retryable": False}) from exc
    except CommandError as exc:
        raise HTTPException(status_code=exc.status, detail={"code": exc.code, "message": exc.message, "retryable": exc.retryable}) from exc


def _browser(request: Request, current: Settings) -> None:
    session = resolve(current, request.cookies.get(COOKIE))
    if session and session.get("status") == "active":
        _require_csrf(request, session)


@router.get("/payments/assistance/configuration")
def read_configuration(current_actor=Depends(actor)) -> dict:
    del current_actor
    return configuration()


@router.get("/payments/assistance/households")
def read_households(q: str | None = None, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: household_directory(current, current_actor["id"], current_actor["organization_id"], q))


@router.get("/payments/assistance/household")
def read_household(tenancy_code: str, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: household_view(current, current_actor["id"], current_actor["organization_id"], tenancy_code))


@router.get("/payments/assistance/measures")
def read_measures(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: owner_measures(current, current_actor["id"], current_actor["organization_id"]))


@router.get("/payments/assistance/queue")
def read_queue(current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    return _call(lambda: queue(current, current_actor["id"], current_actor["organization_id"]))


@router.post("/payments/assistance/determinations")
def create_determination(body: DeterminationBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: record_determination(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/receipts")
def create_receipt(body: ReceiptBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: ingest_receipt(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/receipts/resolve")
def create_resolution(body: ResolveBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: resolve_receipt(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/receipts/apply")
def create_application(body: ApplyBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: apply_receipt(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/batches")
def create_batch(body: BatchBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: record_batch(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/batches/apply")
def create_batch_application(body: BatchApplyBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: apply_batch(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/returns")
def create_required_return(body: ReturnBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: record_required_return(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/returns/complete")
def complete_return(body: ReturnCompletionBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: complete_required_return(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/reports")
def create_report(body: ReportBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: report_transfer(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))


@router.post("/payments/assistance/instructions")
def create_instructions(body: InstructionBody, request: Request, current: Settings = Depends(settings), current_actor=Depends(actor)) -> dict:
    _browser(request, current)
    return _call(lambda: transfer_instructions(current, current_actor["id"], current_actor["organization_id"], body.model_dump()))

import os

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from .catalog import foundation_bundle
from .property import Portfolio
from .seeds import portfolio

router = APIRouter(prefix="/api/foundation", tags=["Phase 0 read-only contracts"])


def require_preview():
    if os.environ.get("PHASE0_ENABLED") != "true":
        raise HTTPException(404, "Seeded contract previews disabled")


def mark_synthetic(response: Response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-PerchPoint-Data"] = "synthetic-phase-0"


def checked_fixture(payload):
    """Reject obvious live-record/credential contamination; never a production serializer.

    Call only with the deterministic seed builders below, never database or provider data.
    These public review endpoints must be retired/disabled before production data is connected.
    """
    forbidden = {"password", "password_hash", "access_token", "refresh_token", "api_key", "client_secret", "private_key", "credential_value"}

    def check(value):
        if isinstance(value, dict):
            unsafe = bool(forbidden.intersection(value))
            if "synthetic" in value or ("schema_version" in value and "id" in value):
                unsafe |= value.get("synthetic") is not True
            if "credential_reference" in value:
                unsafe |= value["credential_reference"] is not None
            if "provider_type" in value:
                unsafe |= value.get("environment") != "synthetic" or value.get("connection_status") != "disconnected"
            if "runtime_enforcement" in value:
                unsafe |= value["runtime_enforcement"] != "not_implemented"
            for key in ("production_authentication", "provider_execution", "canonical_persistence"):
                if key in value:
                    unsafe |= value[key] is not False
            if unsafe:
                raise HTTPException(503, "Synthetic preview unavailable")
            for child in value.values():
                check(child)
        elif isinstance(value, list):
            for child in value:
                check(child)

    check(payload)
    return payload


class FoundationSummary(BaseModel):
    version: str
    data_status: str
    production_authentication: bool
    provider_execution: bool
    canonical_persistence: bool


@router.get("", response_model=FoundationSummary, description="Intentionally public synthetic Phase 0 status only; not a production configuration endpoint.")
async def summary(response: Response):
    require_preview()
    mark_synthetic(response)
    return FoundationSummary(version="0.1.0", data_status="synthetic_contracts_only", production_authentication=False, provider_execution=False, canonical_persistence=False)


@router.get("/portfolio", response_model=Portfolio, description="Intentionally public deterministic fictional portfolio; never production operational records.")
async def get_portfolio(response: Response):
    require_preview()
    mark_synthetic(response)
    return checked_fixture(portfolio().model_dump(mode="json"))


@router.get("/contracts", description="Intentionally public seeded design contracts only. Not live permissions, schemas, configuration, or credentials; disable before production.")
async def get_contracts(response: Response):
    require_preview()
    mark_synthetic(response)
    return checked_fixture(foundation_bundle())
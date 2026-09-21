import os

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from .catalog import foundation_bundle
from .property import Portfolio
from .seeds import portfolio

router = APIRouter(prefix="/api/foundation", tags=["Phase 0 read-only contracts"])


def require_preview():
    if os.environ["PHASE0_ENABLED"] != "true":
        raise HTTPException(404, "Seeded contract previews disabled")


class FoundationSummary(BaseModel):
    version: str
    data_status: str
    production_authentication: bool
    provider_execution: bool
    canonical_persistence: bool


@router.get("", response_model=FoundationSummary)
async def summary():
    require_preview()
    return FoundationSummary(version="0.1.0", data_status="synthetic_contracts_only", production_authentication=False, provider_execution=False, canonical_persistence=False)


@router.get("/portfolio", response_model=Portfolio)
async def get_portfolio():
    require_preview()
    return portfolio()


@router.get("/contracts")
async def get_contracts():
    require_preview()
    return foundation_bundle()
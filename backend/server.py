import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from fastapi import APIRouter, FastAPI, HTTPException, Response
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

from foundation.routes import checked_fixture, mark_synthetic
from foundation.routes import router as foundation_router
from foundation.seeds import portfolio

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="PerchPoint Property Operations API")
api_router = APIRouter(prefix="/api")


class InquiryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    intent: str = Field(min_length=2, max_length=80)
    message: str = Field(default="", max_length=1600)
    property_id: str | None = None
    unit_id: str | None = None
    preferred_date: str | None = None


class InquiryResponse(BaseModel):
    id: str
    status: str
    message: str


class MaintenanceCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    property_address: str = Field(min_length=5, max_length=240)
    unit: str = Field(min_length=1, max_length=80)
    category: str = Field(min_length=2, max_length=80)
    description: str = Field(min_length=10, max_length=2000)
    permission_to_enter: bool = False


class MaintenanceResponse(BaseModel):
    id: str
    status: str
    message: str


def require_demo_submission(email: str):
    if os.environ["PHASE0_ENABLED"] != "true":
        raise HTTPException(503, "Production intake is not implemented")
    if email.rsplit("@", 1)[-1].lower() not in {"example.com", "example.org", "example.net"}:
        raise HTTPException(422, "Synthetic requests only. Use an example.com email and fictional details.")


@api_router.get("/")
async def root():
    return {"message": "PerchPoint property operations API is running"}


@api_router.get("/health")
async def health():
    return {"status": "healthy", "service": "perchpoint"}


@api_router.get("/properties")
async def get_properties():
    return {"properties": [p.model_dump(mode="json") for p in portfolio().properties] if os.environ["PHASE0_ENABLED"] == "true" else [], "data_status": "demonstration_phase_0"}


@api_router.get("/rentals", description="Intentionally public synthetic unit fixtures only. Disabled mode returns an empty catalog, not live inventory.")
async def get_rentals(response: Response):
    mark_synthetic(response)
    return checked_fixture({"units": [u.model_dump(mode="json") for u in portfolio().units] if os.environ.get("PHASE0_ENABLED") == "true" else [], "data_status": "demonstration_phase_0"})


@api_router.post("/leads", response_model=InquiryResponse)
async def create_inquiry(payload: InquiryCreate):
    require_demo_submission(str(payload.email))
    if payload.unit_id:
        unit = next((u for u in portfolio().units if str(u.id) == payload.unit_id), None)
        if not unit or str(unit.property_id) != payload.property_id:
            raise HTTPException(422, "Unit must belong to the referenced canonical property")
    inquiry_id = str(uuid.uuid4())
    document = payload.model_dump()
    document.update({"id": inquiry_id, "email": str(payload.email), "status": "received", "synthetic": True, "created_at": datetime.now(timezone.utc).isoformat()})
    await db.inquiries.insert_one(document)
    return InquiryResponse(id=inquiry_id, status="received", message="Synthetic request recorded. No showing, application, or notification was created.")


@api_router.post("/maintenance-requests", response_model=MaintenanceResponse)
async def create_maintenance_request(payload: MaintenanceCreate):
    require_demo_submission(str(payload.email))
    request_id = f"PP-{uuid.uuid4().hex[:8].upper()}"
    document = payload.model_dump()
    document.update({"id": request_id, "email": str(payload.email), "status": "submitted", "synthetic": True, "created_at": datetime.now(timezone.utc).isoformat()})
    await db.maintenance_requests.insert_one(document)
    return MaintenanceResponse(id=request_id, status="submitted", message="Synthetic maintenance request recorded. No dispatch or notification was sent.")


app.include_router(api_router)
app.include_router(foundation_router)
app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ["CORS_ORIGINS"].split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
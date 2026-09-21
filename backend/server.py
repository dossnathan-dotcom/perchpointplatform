from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import os
import uuid

from dotenv import load_dotenv
from fastapi import FastAPI, APIRouter
from motor.motor_asyncio import AsyncIOMotorClient
from pydantic import BaseModel, EmailStr, Field
from starlette.middleware.cors import CORSMiddleware

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
    property_id: Optional[str] = None
    preferred_date: Optional[str] = None


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


RENTALS = [
    {"id": "412-elm-unit-a", "property_id": "412-elm", "unit": "412-A", "type": "mixed_use", "use": "residential", "rent": 2250, "deposit": 2250, "status": "available_now"},
    {"id": "clifton-duplex-unit-b", "property_id": "clifton-avenue-duplex", "unit": "Residence B", "type": "duplex", "use": "residential", "rent": 1650, "deposit": 1650, "status": "available_soon"},
    {"id": "otr-triplex-unit-3", "property_id": "otr-heritage-triplex", "unit": "Unit 3", "type": "triplex", "use": "residential", "rent": 1950, "deposit": 1950, "status": "available_soon"},
    {"id": "412-elm-commercial-c1", "property_id": "412-elm", "unit": "412-C1", "type": "mixed_use", "use": "commercial", "rent": 3800, "deposit": 7600, "status": "future_availability"},
]


@api_router.get("/")
async def root():
    return {"message": "PerchPoint property operations API is running"}


@api_router.get("/health")
async def health():
    return {"status": "healthy", "service": "perchpoint"}


@api_router.get("/properties")
async def get_properties():
    return {"properties": RENTALS, "data_status": "demonstration_phase_0"}


@api_router.post("/leads", response_model=InquiryResponse)
async def create_inquiry(payload: InquiryCreate):
    inquiry_id = str(uuid.uuid4())
    document = payload.model_dump()
    document.update({"id": inquiry_id, "email": str(payload.email), "status": "received", "created_at": datetime.now(timezone.utc).isoformat()})
    await db.inquiries.insert_one(document)
    return InquiryResponse(id=inquiry_id, status="received", message="Your request is in. HawkVision will follow up with the next step.")


@api_router.post("/maintenance-requests", response_model=MaintenanceResponse)
async def create_maintenance_request(payload: MaintenanceCreate):
    request_id = f"PP-{uuid.uuid4().hex[:8].upper()}"
    document = payload.model_dump()
    document.update({"id": request_id, "email": str(payload.email), "status": "submitted", "created_at": datetime.now(timezone.utc).isoformat()})
    await db.maintenance_requests.insert_one(document)
    return MaintenanceResponse(id=request_id, status="submitted", message="Your maintenance request has been recorded for review.")


app.include_router(api_router)
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
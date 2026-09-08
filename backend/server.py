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

mongo_url = os.environ["MONGO_URL"]
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ["DB_NAME"]]

app = FastAPI(title="HawkVision Homes API")
api_router = APIRouter(prefix="/api")


class LeadCreate(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    intent: str = Field(min_length=2, max_length=80)
    message: str = Field(default="", max_length=1200)
    property_id: Optional[str] = None
    preferred_date: Optional[str] = None


class LeadResponse(BaseModel):
    id: str
    status: str
    message: str


class ValuationCreate(BaseModel):
    address: str = Field(min_length=5, max_length=200)
    property_type: str
    beds: int = Field(ge=0, le=20)
    baths: float = Field(ge=0, le=20)
    condition: str
    email: Optional[EmailStr] = None


class ValuationResponse(BaseModel):
    id: str
    address: str
    estimate_low: int
    estimate_high: int
    confidence: str
    message: str


PROPERTIES = [
    {
        "id": "mt-adams-overlook",
        "title": "Mount Adams Skyline Overlook",
        "neighborhood": "Mount Adams",
        "price": 1285000,
        "beds": 4,
        "baths": 3.5,
        "sqft": 3820,
        "status": "Private portfolio",
    },
    {
        "id": "indian-hill-sanctuary",
        "title": "Indian Hill Equestrian Sanctuary",
        "neighborhood": "Indian Hill",
        "price": 2495000,
        "beds": 6,
        "baths": 5.5,
        "sqft": 7400,
        "status": "Exclusive",
    },
    {
        "id": "hyde-park-classic",
        "title": "Hyde Park Restored Classic",
        "neighborhood": "Hyde Park",
        "price": 875000,
        "beds": 4,
        "baths": 3,
        "sqft": 2960,
        "status": "New this week",
    },
    {
        "id": "otr-penthouse",
        "title": "Over-The-Rhine Historic Penthouse",
        "neighborhood": "Over-The-Rhine",
        "price": 1190000,
        "beds": 3,
        "baths": 3,
        "sqft": 2480,
        "status": "By appointment",
    },
]


@api_router.get("/")
async def root():
    return {"message": "HawkVision Homes API is running"}


@api_router.get("/health")
async def health():
    return {"status": "healthy", "service": "hawkvision-homes"}


@api_router.get("/properties")
async def get_properties():
    return {"properties": PROPERTIES}


@api_router.post("/leads", response_model=LeadResponse)
async def create_lead(payload: LeadCreate):
    lead_id = str(uuid.uuid4())
    doc = payload.model_dump()
    doc.update(
        {
            "id": lead_id,
            "email": str(payload.email),
            "status": "received",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await db.leads.insert_one(doc)
    return LeadResponse(
        id=lead_id,
        status="received",
        message="Thanks — a HawkVision advisor will follow up shortly.",
    )


@api_router.post("/valuation", response_model=ValuationResponse)
async def create_valuation(payload: ValuationCreate):
    base_values = {
        "condo": 310000,
        "single_family": 585000,
        "luxury_estate": 1250000,
        "multi_family": 720000,
    }
    condition_multiplier = {
        "needs_work": 0.88,
        "well_kept": 1.0,
        "updated": 1.09,
        "renovated": 1.18,
    }
    base = base_values.get(payload.property_type, base_values["single_family"])
    estimate = base + (payload.beds * 76000) + (payload.baths * 42000)
    estimate *= condition_multiplier.get(payload.condition, 1.0)
    estimate_low = int((estimate * 0.965) / 5000) * 5000
    estimate_high = int((estimate * 1.045) / 5000) * 5000
    valuation_id = str(uuid.uuid4())

    doc = payload.model_dump()
    doc.update(
        {
            "id": valuation_id,
            "email": str(payload.email) if payload.email else None,
            "estimate_low": estimate_low,
            "estimate_high": estimate_high,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    await db.valuation_requests.insert_one(doc)

    return ValuationResponse(
        id=valuation_id,
        address=payload.address,
        estimate_low=estimate_low,
        estimate_high=estimate_high,
        confidence="Preliminary Cincinnati range",
        message="Your instant range is ready. A local advisor can refine it with off-market comps.",
    )


app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get("CORS_ORIGINS", "*").split(","),
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()

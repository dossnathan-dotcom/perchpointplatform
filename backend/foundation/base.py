from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

Identifier = UUID
NonNegative = Annotated[int, Field(ge=0)]
Sensitivity = Literal["public", "internal", "confidential", "restricted"]


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Record(Contract):
    id: Identifier
    schema_version: Literal["0.1.0"] = "0.1.0"
    synthetic: bool = True


class Scope(Contract):
    organization_id: Identifier
    ownership_entity_id: Identifier | None = None
    property_id: Identifier | None = None
    building_id: Identifier | None = None
    unit_id: Identifier | None = None
    household_id: Identifier | None = None
    assignment_id: Identifier | None = None


class Period(Contract):
    effective_at: datetime
    expires_at: datetime | None = None


class Money(Contract):
    amount_minor: NonNegative
    currency: Annotated[str, Field(pattern=r"^[A-Z]{3}$")]
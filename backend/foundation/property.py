from typing import Literal

from pydantic import Field, model_validator

from .base import Contract, Identifier, Money, Record

PropertyType = Literal["single_family", "duplex", "triplex", "multifamily", "commercial", "mixed_use"]


class Address(Contract):
    line1: str
    country: str = Field(min_length=2)
    state: str
    county: str
    municipality: str
    postal_code: str
    is_example: bool


class Organization(Record):
    name: str


class OwnershipEntity(Record):
    organization_id: Identifier
    legal_name: str
    entity_type: Literal["company", "llc", "trust", "individual", "other"]
    management_relationship: Literal["owned", "third_party_managed"]


class Property(Record):
    organization_id: Identifier
    ownership_entity_id: Identifier
    name: str
    property_type: PropertyType
    address: Address
    parcel_references: list[str] = Field(default_factory=list)


class Building(Record):
    organization_id: Identifier
    property_id: Identifier
    name: str
    allowed_uses: list[Literal["residential", "commercial"]] = Field(min_length=1)


class ResidentialTerms(Contract):
    bedrooms: int = Field(ge=0)
    bathrooms: float = Field(ge=0)
    monthly_rent: Money
    security_deposit: Money
    application_fee: Money
    utilities: str
    pet_policy: str


class CommercialTerms(Contract):
    intended_use: str
    base_rent: Money
    rent_period: Literal["month", "year"]
    deposit: Money
    lease_type: str
    cam_nnn_terms: str
    utility_responsibility: str
    zoning_notes: str
    loading_access: str
    parking: str
    build_out_status: str


class Unit(Record):
    organization_id: Identifier
    property_id: Identifier
    building_id: Identifier
    label: str
    use: Literal["residential", "commercial"]
    square_feet: int = Field(gt=0)
    status: Literal["available", "occupied", "unavailable"]
    available_date: str | None = None
    residential: ResidentialTerms | None = None
    commercial: CommercialTerms | None = None
    image_key: str

    @model_validator(mode="after")
    def discriminated_terms(self):
        if self.use == "residential" and (self.residential is None or self.commercial is not None):
            raise ValueError("Residential units require only residential terms")
        if self.use == "commercial" and (self.commercial is None or self.residential is not None):
            raise ValueError("Commercial units require only commercial terms")
        return self


class Location(Record):
    organization_id: Identifier
    property_id: Identifier
    building_id: Identifier | None = None
    unit_id: Identifier | None = None
    name: str


class SharedSpace(Location):
    kind: Literal["entry", "hallway", "parking", "roof", "basement", "laundry", "utility_room", "exterior", "other"]

    @model_validator(mode="after")
    def shared_not_private(self):
        if self.unit_id:
            raise ValueError("Shared spaces belong to property/building, not a private unit")
        return self


class Asset(Location):
    shared_space_id: Identifier | None = None
    kind: Literal["hvac", "appliance", "meter", "access", "plumbing", "building_system", "other"]


class Portfolio(Contract):
    organizations: list[Organization]
    ownership_entities: list[OwnershipEntity]
    properties: list[Property]
    buildings: list[Building]
    units: list[Unit]
    shared_spaces: list[SharedSpace]
    assets: list[Asset]

    @model_validator(mode="after")
    def relationships(self):
        groups = [self.organizations, self.ownership_entities, self.properties, self.buildings, self.units, self.shared_spaces, self.assets]
        ids = [r.id for group in groups for r in group]
        if len(ids) != len(set(ids)):
            raise ValueError("Canonical IDs must be globally unique")
        orgs = {r.id: r for r in self.organizations}
        owners = {r.id: r for r in self.ownership_entities}
        props = {r.id: r for r in self.properties}
        buildings = {r.id: r for r in self.buildings}
        units = {r.id: r for r in self.units}
        spaces = {r.id: r for r in self.shared_spaces}
        for group in groups[1:]:
            for record in group:
                if record.organization_id not in orgs:
                    raise ValueError("Unknown organization")
        for prop in self.properties:
            owner = owners.get(prop.ownership_entity_id)
            if not owner or owner.organization_id != prop.organization_id:
                raise ValueError("Ownership entity outside organization")
        for record in [*self.buildings, *self.units, *self.shared_spaces, *self.assets]:
            prop = props.get(record.property_id)
            if not prop or prop.organization_id != record.organization_id:
                raise ValueError("Property outside organization")
            building_id = getattr(record, "building_id", None)
            if building_id:
                building = buildings.get(building_id)
                if not building or building.property_id != record.property_id:
                    raise ValueError("Building outside property")
            unit_id = getattr(record, "unit_id", None)
            if unit_id:
                unit = units.get(unit_id)
                if not unit or unit.property_id != record.property_id or unit.building_id != building_id:
                    raise ValueError("Unit outside building/property")
            shared_id = getattr(record, "shared_space_id", None)
            if shared_id:
                shared = spaces.get(shared_id)
                if not shared or shared.property_id != record.property_id or shared.building_id != building_id or unit_id:
                    raise ValueError("Asset outside shared location")
        for unit in self.units:
            if unit.use not in buildings[unit.building_id].allowed_uses:
                raise ValueError("Unit use not permitted in building")
            prop_type = props[unit.property_id].property_type
            if (prop_type == "commercial" and unit.use != "commercial") or (prop_type not in ("commercial", "mixed_use") and unit.use != "residential"):
                raise ValueError("Unit use conflicts with property type")
        for prop in self.properties:
            children = [u for u in self.units if u.property_id == prop.id]
            structures = [b for b in self.buildings if b.property_id == prop.id]
            required = {"single_family": 1, "duplex": 2, "triplex": 3}.get(prop.property_type)
            if not structures or not children:
                raise ValueError("Complete portfolio requires a building and rentable unit per property")
            if required and (len(children) != required or len(structures) != 1):
                raise ValueError("Single-family/duplex/triplex shape mismatch")
        return self
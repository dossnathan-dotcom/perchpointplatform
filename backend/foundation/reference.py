"""Phase 2 reference-slice contracts (schema 0.2.0).

These types are separately versioned. They do not redefine Phase 0 Record fields.
Pydantic model validators here are not automatically enforced by generated JSON
Schema or TypeScript. Database referential integrity is not claimed.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import Field, model_validator

from .base import Contract, Identifier, Money, Scope
from .property import Address, CommercialTerms, PropertyType, ResidentialTerms

REFERENCE_VERSION: Literal["0.2.0"] = "0.2.0"

Condition = Literal["rent_ready", "renovation", "damaged", "unknown"]
OccupancyState = Literal["vacant", "occupied", "notice", "unknown"]
AvailabilityState = Literal["offerable", "withheld", "unknown"]
PublicationState = Literal["unpublished", "published", "withdrawn"]
MaintenanceRestriction = Literal["none", "limited_access", "unsafe", "unknown"]
LegalRestriction = Literal["none", "hold", "litigation", "unknown"]
Phase0UnitStatus = Literal["available", "occupied", "unavailable"]
MappingConfidence = Literal["derived", "ambiguous", "explicit"]
PortalAccessKind = Literal["primary", "additional"]
InquiryIntent = Literal["showing", "application", "contact", "other"]
TriageDecision = Literal["new", "assigned", "waiting", "closed_duplicate", "closed_not_pursuing"]


class ReferenceRecord(Contract):
    id: Identifier
    schema_version: Literal["0.2.0"] = REFERENCE_VERSION
    synthetic: bool = True


class InclusiveExclusiveDateRange(Contract):
    """effective_on is inclusive. ended_on is exclusive. Open-ended when ended_on is null."""

    effective_on: date
    ended_on: date | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.ended_on is not None and self.ended_on <= self.effective_on:
            raise ValueError("ended_on must be after effective_on (end exclusive)")
        return self


class InclusiveExclusiveDateTimeRange(Contract):
    """effective_at is inclusive. ended_at is exclusive. Open-ended when ended_at is null."""

    effective_at: datetime
    ended_at: datetime | None = None

    @model_validator(mode="after")
    def ordered(self):
        if self.ended_at is not None and self.ended_at <= self.effective_at:
            raise ValueError("ended_at must be after effective_at (end exclusive)")
        return self


class OwnershipRelationship(ReferenceRecord):
    organization_id: Identifier
    legal_entity_id: Identifier
    property_id: Identifier
    interval: InclusiveExclusiveDateRange
    note: str | None = None


class ManagementRelationship(ReferenceRecord):
    organization_id: Identifier
    manager_organization_id: Identifier
    property_id: Identifier
    interval: InclusiveExclusiveDateRange
    note: str | None = None


class PortfolioGroup(ReferenceRecord):
    organization_id: Identifier
    label: str


class PortfolioMembership(ReferenceRecord):
    organization_id: Identifier
    group_id: Identifier
    property_id: Identifier
    interval: InclusiveExclusiveDateRange


class OccupancyRelationship(ReferenceRecord):
    organization_id: Identifier
    space_id: Identifier
    household_id: Identifier | None = None
    business_party_id: Identifier | None = None
    interval: InclusiveExclusiveDateTimeRange

    @model_validator(mode="after")
    def party_present(self):
        if bool(self.household_id) == bool(self.business_party_id):
            raise ValueError("Occupancy requires exactly one of household_id or business_party_id")
        return self


class HouseholdPortalAccess(ReferenceRecord):
    organization_id: Identifier
    household_id: Identifier
    person_id: Identifier
    account_id: Identifier
    kind: PortalAccessKind
    interval: InclusiveExclusiveDateTimeRange
    authorization_reason: str


class SpaceOperatingState(ReferenceRecord):
    organization_id: Identifier
    space_id: Identifier
    condition: Condition
    occupancy: OccupancyState
    availability: AvailabilityState
    publication: PublicationState
    maintenance_restriction: MaintenanceRestriction
    legal_restriction: LegalRestriction
    condition_source: MappingConfidence
    occupancy_source: MappingConfidence
    availability_source: MappingConfidence
    publication_source: MappingConfidence
    maintenance_restriction_source: MappingConfidence
    legal_restriction_source: MappingConfidence
    mapping_notes: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def publication_requires_offerable(self):
        if self.publication == "published" and self.availability != "offerable":
            raise ValueError("Published spaces must be offerable")
        if self.publication == "published" and self.legal_restriction != "none":
            raise ValueError("Published spaces cannot carry a legal restriction")
        if self.occupancy == "occupied" and self.availability == "offerable":
            raise ValueError("Occupied spaces cannot be offerable")
        return self


SPACE_STATE_TRANSITIONS: dict[str, dict[str, tuple[str, ...]]] = {
    "condition": {
        "unknown": ("rent_ready", "renovation", "damaged"),
        "rent_ready": ("renovation", "damaged"),
        "renovation": ("rent_ready", "damaged"),
        "damaged": ("renovation", "rent_ready"),
    },
    "occupancy": {
        "unknown": ("vacant", "occupied", "notice"),
        "vacant": ("occupied",),
        "occupied": ("notice", "vacant"),
        "notice": ("vacant", "occupied"),
    },
    "availability": {
        "unknown": ("offerable", "withheld"),
        "offerable": ("withheld",),
        "withheld": ("offerable",),
    },
    "publication": {
        "unpublished": ("published",),
        "published": ("withdrawn", "unpublished"),
        "withdrawn": ("unpublished", "published"),
    },
    "maintenance_restriction": {
        "unknown": ("none", "limited_access", "unsafe"),
        "none": ("limited_access", "unsafe"),
        "limited_access": ("none", "unsafe"),
        "unsafe": ("limited_access", "none"),
    },
    "legal_restriction": {
        "unknown": ("none", "hold", "litigation"),
        "none": ("hold", "litigation"),
        "hold": ("none", "litigation"),
        "litigation": ("hold", "none"),
    },
}


def allowed_space_transition(dimension: str, current: str, nxt: str) -> bool:
    return nxt in SPACE_STATE_TRANSITIONS[dimension][current]


def project_phase0_unit_status(status: Phase0UnitStatus) -> dict[str, object]:
    """Compatibility projection. Does not invent legal, publication, or dated occupancy facts."""
    notes: list[str] = [
        "Phase 0 Unit.status cannot determine condition, publication, maintenance, or legal restriction"
    ]
    if status == "occupied":
        occupancy, occupancy_source = "occupied", "derived"
        availability, availability_source = "withheld", "derived"
    elif status == "available":
        occupancy, occupancy_source = "unknown", "ambiguous"
        availability, availability_source = "offerable", "derived"
        notes.append("available does not prove historical vacancy dates or publication")
    else:
        occupancy, occupancy_source = "unknown", "ambiguous"
        availability, availability_source = "withheld", "derived"
        notes.append("unavailable does not distinguish maintenance, legal, or renovation causes")
    return {
        "condition": "unknown",
        "occupancy": occupancy,
        "availability": availability,
        "publication": "unpublished",
        "maintenance_restriction": "unknown",
        "legal_restriction": "unknown",
        "condition_source": "ambiguous",
        "occupancy_source": occupancy_source,
        "availability_source": availability_source,
        "publication_source": "ambiguous",
        "maintenance_restriction_source": "ambiguous",
        "legal_restriction_source": "ambiguous",
        "mapping_notes": notes,
    }


class UntrustedRequestInput(Contract):
    """External request metadata. Never treated as authenticated actor context."""

    idempotency_key: str = Field(min_length=8, max_length=128)
    request_fingerprint: str = Field(min_length=8, max_length=128)
    correlation_id: Identifier
    client_observed_at: datetime | None = None


class TrustedActorContext(Contract):
    """Server-resolved actor. Must not appear on public or generic update payloads."""

    actor_id: Identifier
    organization_id: Identifier
    delegated_authority_id: Identifier | None = None
    membership_ids: list[Identifier] = Field(default_factory=list)
    feature_flags: list[str] = Field(default_factory=list)


class ExpectedVersion(Contract):
    aggregate_id: Identifier
    expected_version: int = Field(ge=1)


class SafeErrorDetail(Contract):
    field: str | None = None
    reason: str


class SafeErrorEnvelope(Contract):
    code: str
    message: str
    correlation_id: Identifier
    details: list[SafeErrorDetail] = Field(default_factory=list)
    retryable: bool
    required_action: str | None = None
    permission_safe: Literal[True] = True


class CommandResult(ReferenceRecord):
    accepted: bool
    result_code: str
    correlation_id: Identifier
    aggregate_id: Identifier | None = None
    aggregate_version: int | None = Field(default=None, ge=1)
    replayed: bool = False
    message: str


class CreateProperty(Contract):
    name: str = Field(min_length=2, max_length=160)
    property_type: PropertyType
    address: Address
    parcel_references: list[str] = Field(default_factory=list)
    request: UntrustedRequestInput
    expected_version: ExpectedVersion | None = None


class UpdateProperty(Contract):
    property_id: Identifier
    name: str | None = None
    address: Address | None = None
    parcel_references: list[str] | None = None
    request: UntrustedRequestInput
    expected_version: ExpectedVersion


class CreateBuilding(Contract):
    property_id: Identifier
    name: str = Field(min_length=1, max_length=80)
    allowed_uses: list[Literal["residential", "commercial"]] = Field(min_length=1)
    request: UntrustedRequestInput
    expected_version: ExpectedVersion | None = None


class CreateLeasableSpace(Contract):
    property_id: Identifier
    building_id: Identifier
    label: str = Field(min_length=1, max_length=80)
    use: Literal["residential", "commercial"]
    square_feet: int = Field(gt=0)
    residential: ResidentialTerms | None = None
    commercial: CommercialTerms | None = None
    request: UntrustedRequestInput
    expected_version: ExpectedVersion | None = None

    @model_validator(mode="after")
    def exclusive_terms(self):
        if self.use == "residential" and (self.residential is None or self.commercial is not None):
            raise ValueError("Residential spaces require only residential terms")
        if self.use == "commercial" and (self.commercial is None or self.residential is not None):
            raise ValueError("Commercial spaces require only commercial terms")
        return self


class UpdateLeasableSpace(Contract):
    space_id: Identifier
    label: str | None = None
    square_feet: int | None = Field(default=None, gt=0)
    residential: ResidentialTerms | None = None
    commercial: CommercialTerms | None = None
    request: UntrustedRequestInput
    expected_version: ExpectedVersion


class SetSpaceAvailability(Contract):
    space_id: Identifier
    availability: AvailabilityState
    request: UntrustedRequestInput
    expected_version: ExpectedVersion


class SetSpacePublication(Contract):
    space_id: Identifier
    publication: PublicationState
    request: UntrustedRequestInput
    expected_version: ExpectedVersion


class SubmitPublicInquiry(Contract):
    """Public write. Does not grant staff identity or read of internal records."""

    listing_id: Identifier
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(min_length=6, max_length=254)
    intent: InquiryIntent
    message: str = Field(default="", max_length=1600)
    preferred_date: date | None = None
    request: UntrustedRequestInput


class PublicInquiryAcknowledgement(Contract):
    inquiry_id: Identifier
    status: Literal["received"]
    synthetic: Literal[True] = True
    message: str
    correlation_id: Identifier
    abuse_control: Literal["rate_limit_and_fingerprint_required"]
    retry_semantics: Literal["identical_key_and_fingerprint_replays_ack"]


class TriageInquiry(Contract):
    inquiry_id: Identifier
    decision: TriageDecision
    note: str = Field(max_length=500)
    request: UntrustedRequestInput
    expected_version: ExpectedVersion


class PublishedListingRead(Contract):
    listing_id: Identifier
    space_id: Identifier
    property_name: str
    label: str
    use: Literal["residential", "commercial"]
    municipality: str
    state: str
    publication: Literal["published"]
    availability: Literal["offerable"]
    monthly_amount: Money
    available_date: date | None = None
    synthetic: Literal[True] = True


class StaffInquiryRead(ReferenceRecord):
    listing_id: Identifier
    organization_id: Identifier
    space_id: Identifier
    status: TriageDecision
    name: str
    email: str
    intent: InquiryIntent
    message: str
    preferred_date: date | None = None
    assigned_staff_id: Identifier | None = None
    received_at: datetime
    version: int = Field(ge=1)


class ActivityHistoryRead(ReferenceRecord):
    organization_id: Identifier
    resource_type: str
    resource_id: Identifier
    summary: str
    occurred_at: datetime
    actor_id: Identifier | None = None
    visibility: Literal["staff", "resident", "public"]


class TaskExampleRead(ReferenceRecord):
    organization_id: Identifier
    title: str
    status: Literal["open", "waiting", "done"]
    owner_id: Identifier | None = None
    due_on: date | None = None
    next_action: str
    engine: Literal["read_only_example"] = "read_only_example"


class ApprovalExampleRead(ReferenceRecord):
    organization_id: Identifier
    title: str
    state: Literal["pending", "approved", "denied"]
    amount: Money | None = None
    engine: Literal["read_only_example"] = "read_only_example"


class PageQuery(Contract):
    limit: int = Field(ge=1, le=100)
    cursor: str | None = None


class PageResult(Contract):
    next_cursor: str | None = None
    total_count: int | None = Field(default=None, ge=0)
    applied_authorization: Literal["same_predicate_as_list"]


class ReferenceDomainEvent(ReferenceRecord):
    event_type: Literal[
        "listing.published.v1",
        "listing.withdrawn.v1",
        "inquiry.submitted.v1",
        "inquiry.triaged.v1",
        "activity.recorded.v1",
        "property.space_states_projected.v1",
    ]
    aggregate_id: Identifier
    aggregate_version: int = Field(ge=1)
    organization_id: Identifier
    occurred_at: datetime
    correlation_id: Identifier
    causation_id: Identifier | None = None
    payload_record_ids: list[Identifier] = Field(default_factory=list)


class ReferenceAuditEntry(ReferenceRecord):
    actor_id: Identifier | None
    delegated_authority_id: Identifier | None = None
    action: str
    resource_type: str
    resource_id: Identifier
    scope: Scope
    occurred_at: datetime
    correlation_id: Identifier
    result: Literal["allowed", "denied", "failed", "replayed"]
    previous_event_hash: str | None = None
    event_hash: str
    redacted: Literal[True] = True


class DeliveryAttempt(ReferenceRecord):
    outbox_id: Identifier
    attempt_number: int = Field(ge=1)
    started_at: datetime
    finished_at: datetime | None = None
    outcome: Literal["delivered", "retryable", "dead_letter"]
    repeats_business_decision: Literal[False] = False


class FakeProviderCommand(Contract):
    operation: Literal["echo", "signed_webhook"]
    organization_id: Identifier
    idempotency_key: str
    payload_record_ids: list[Identifier] = Field(default_factory=list)


class FakeProviderResult(Contract):
    accepted: bool
    live_network: Literal[False] = False
    status: Literal["synthetic_ok", "synthetic_rejected"]
    provider_event_id: str | None = None


class ReferenceSlice(Contract):
    schema_version: Literal["0.2.0"] = REFERENCE_VERSION
    ownership: list[OwnershipRelationship]
    management: list[ManagementRelationship]
    groups: list[PortfolioGroup]
    memberships: list[PortfolioMembership]
    occupancies: list[OccupancyRelationship]
    portal_access: list[HouseholdPortalAccess]
    space_states: list[SpaceOperatingState]
    published_listings: list[PublishedListingRead]
    known_organization_ids: list[Identifier]
    known_property_ids: list[Identifier]
    known_space_ids: list[Identifier]
    known_entity_ids: list[Identifier]
    known_household_ids: list[Identifier]
    known_person_ids: list[Identifier]
    known_account_ids: list[Identifier]

    @model_validator(mode="after")
    def scoped_relationships(self):
        orgs = set(self.known_organization_ids)
        props = set(self.known_property_ids)
        spaces = set(self.known_space_ids)
        entities = set(self.known_entity_ids)
        households = set(self.known_household_ids)
        people = set(self.known_person_ids)
        accounts = set(self.known_account_ids)
        for rel in self.ownership:
            if rel.organization_id not in orgs or rel.property_id not in props or rel.legal_entity_id not in entities:
                raise ValueError("Ownership relationship outside known organization graph")
        for rel in self.management:
            if rel.organization_id not in orgs or rel.manager_organization_id not in orgs or rel.property_id not in props:
                raise ValueError("Management relationship outside known organization graph")
        groups = {g.id: g for g in self.groups}
        for mem in self.memberships:
            group = groups.get(mem.group_id)
            if not group or group.organization_id != mem.organization_id or mem.property_id not in props:
                raise ValueError("Portfolio membership outside organization")
        for occ in self.occupancies:
            if occ.organization_id not in orgs or occ.space_id not in spaces:
                raise ValueError("Occupancy outside organization or space")
            if occ.household_id and occ.household_id not in households:
                raise ValueError("Occupancy household unknown")
        primaries: set[UUID] = set()
        for access in self.portal_access:
            if (
                access.organization_id not in orgs
                or access.household_id not in households
                or access.person_id not in people
                or access.account_id not in accounts
            ):
                raise ValueError("Portal access outside known identities")
            if access.kind == "primary" and access.interval.ended_at is None:
                if access.household_id in primaries:
                    raise ValueError("Only one active primary portal account per household")
                primaries.add(access.household_id)
        for state in self.space_states:
            if state.organization_id not in orgs or state.space_id not in spaces:
                raise ValueError("Space state outside organization")
        for listing in self.published_listings:
            if listing.space_id not in spaces:
                raise ValueError("Published listing space unknown")
        return self

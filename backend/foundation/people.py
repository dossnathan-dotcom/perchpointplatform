from datetime import datetime
from typing import Literal

from pydantic import Field, model_validator

from .base import Contract, Identifier, Record

RelationshipKind = Literal["applicant", "co_applicant", "primary_holder", "adult_signer", "occupant", "minor_occupant", "guarantor", "resident", "former_resident", "emergency_contact", "staff", "maintenance_employee", "subcontractor", "vendor_contact", "business_applicant", "business_tenant"]


class Person(Record):
    display_name: str
    age_class: Literal["adult", "minor", "unknown"]
    identity_status: Literal["unverified", "verified", "synthetic"]


class UserAccount(Record):
    person_id: Identifier
    status: Literal["invited", "active", "suspended", "deactivated", "synthetic"]
    identity_provider_reference: Identifier | None = None
    # Passwords and tokens are deliberately not part of this record.


class Household(Record):
    organization_id: Identifier
    label: str
    status: Literal["applicant", "resident", "former"]


class BusinessParty(Record):
    organization_id: Identifier
    legal_name: str
    kind: Literal["applicant", "tenant", "vendor"]


class PersonRelationship(Record):
    person_id: Identifier
    organization_id: Identifier
    kind: RelationshipKind
    household_id: Identifier | None = None
    unit_id: Identifier | None = None
    business_party_id: Identifier | None = None
    account_id: Identifier | None = None
    attributable_access_required: bool = False
    effective_at: datetime
    ended_at: datetime | None = None

    @model_validator(mode="after")
    def time_order(self):
        if self.ended_at and self.ended_at <= self.effective_at:
            raise ValueError("Relationship end must follow start")
        return self


class PeopleGraph(Contract):
    people: list[Person]
    accounts: list[UserAccount]
    households: list[Household]
    businesses: list[BusinessParty]
    relationships: list[PersonRelationship]
    # Reference sets supplied from the canonical portfolio, not role-specific copies.
    organization_ids: list[Identifier]
    unit_organizations: dict[str, Identifier] = Field(default_factory=dict)

    @model_validator(mode="after")
    def identities_and_relationships(self):
        all_records = [*self.people, *self.accounts, *self.households, *self.businesses, *self.relationships]
        if len({r.id for r in all_records}) != len(all_records):
            raise ValueError("Duplicate canonical identity")
        persons = {p.id: p for p in self.people}
        accounts = {a.id: a for a in self.accounts}
        households = {h.id: h for h in self.households}
        businesses = {b.id: b for b in self.businesses}
        if len({a.person_id for a in self.accounts}) != len(self.accounts):
            raise ValueError("One canonical account per person; no duplicate identity by role")
        if any(a.person_id not in persons for a in self.accounts):
            raise ValueError("Account requires a person")
        primaries = set()
        for record in [*self.households, *self.businesses, *self.relationships]:
            if record.organization_id not in self.organization_ids:
                raise ValueError("Unknown organization")
        for r in self.relationships:
            person = persons.get(r.person_id)
            if not person:
                raise ValueError("Relationship requires canonical person")
            if r.unit_id and self.unit_organizations.get(str(r.unit_id)) != r.organization_id:
                raise ValueError("Unit relationship outside organization")
            if r.household_id and (r.household_id not in households or households[r.household_id].organization_id != r.organization_id):
                raise ValueError("Household outside organization")
            if r.business_party_id and (r.business_party_id not in businesses or businesses[r.business_party_id].organization_id != r.organization_id):
                raise ValueError("Business relationship outside organization")
            account = accounts.get(r.account_id)
            if r.account_id and (not account or account.person_id != r.person_id):
                raise ValueError("Accounts cannot be shared")
            if r.kind in ("primary_holder", "adult_signer", "co_applicant", "guarantor") and person.age_class != "adult":
                raise ValueError("Adult relationship requires an adult person")
            if r.kind == "minor_occupant" and person.age_class != "minor":
                raise ValueError("Minor occupant requires minor classification")
            if (r.attributable_access_required or r.kind in ("adult_signer", "primary_holder")) and not account:
                raise ValueError("Attributable access requires an individual account reference")
            if r.kind == "primary_holder":
                if not r.household_id:
                    raise ValueError("Primary holder requires household")
                if not r.ended_at:
                    if r.household_id in primaries:
                        raise ValueError("Only one active primary household holder")
                    primaries.add(r.household_id)
        return self
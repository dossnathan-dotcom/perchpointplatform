# Canonical terminology and entity relationships

## Real-estate graph
`Organization → OwnershipEntity → Property → Building → Unit`

- Organization: operating management organization (HawkVision or future operator).
- Ownership entity: legal owner/controller, with `owned` or `third_party_managed` management relationship.
- Property: legal/operating site, structured address and parcel context, not a physical building or a listing.
- Building: physical structure at exactly one property.
- Unit: independently leased/occupied residential or commercial space in exactly one building/property.
- Shared space: common entry/hallway/parking/roof/basement/laundry/utility/exterior location at property or building scope.
- Asset: HVAC/appliance/meter/access/plumbing/building-system equipment at property/building/unit/shared-space scope.

The arrow in a conceptual hierarchy is **not** a rule that all shared spaces belong under a unit. Property parking need not be forced under Building 1. Roof equipment can attach to the roof shared-space record. Unit-specific assets require the matching building and property. Public `rentals` are projections of units, not a new entity type.

## Executable constraints (`Portfolio`)
Globally unique UUIDs within the aggregate; existing organization references; owner and property in the same organization; building belongs to the selected property; unit belongs to the selected building; asset/shared-space locations agree with their property/building. Shared spaces cannot have a private unit. Shared-space assets cannot simultaneously be private-unit assets.
Residential and commercial terms are exclusive. Unit use must be allowed by the building and property type. Complete fixture aggregates require at least one building and unit. Single-family, duplex and triplex fixtures require exactly 1/2/3 residential units and one building. Incremental construction/draft aggregates are a future design decision.

Residential terms include bedrooms, bathrooms, rent, deposit, application fee, utilities and pet policy. Commercial terms include intended use, base rent/period, deposit, lease type, CAM/NNN, utility responsibility, zoning/use notes, loading/access, parking and build-out status. Both have area, status and available date. The UI never renders residential beds/baths for a commercial unit.

## Person graph
- `Person`: unique human identity across time, relationships and organizations.
- `UserAccount`: login identity reference associated with one person; no password/token fields in these contracts.
- `Household`: organization-scoped group; applicant/resident/former status is not the person’s permanent type.
- `PersonRelationship`: attributable, time-bounded role connecting a person to household/unit/business/organization.
- `BusinessParty`: business applicant, tenant or vendor, with human contacts represented as person relationships.

Relationship inventory: applicant, co-applicant, primary household holder, adult signer, occupant, minor occupant, guarantor, resident, former resident, business applicant, business tenant, emergency contact, staff, maintenance employee, subcontractor and vendor contact.

One active primary holder per household; each signer uses their own account reference. Accounts cannot point to a different person than the relationship. Adult/minor relationship checks are explicit. End dates follow start dates. Organization and unit/household/business references must match. No duplicate person is created just because their role changes. Record deletion is not the move-out/deactivation model: end relationships and revoke access while preserving historical attribution.

No real identity verification is claimed. The seed uses `synthetic` identity/account status. Future verified identity proof, deduplication and merge/split audit must be approved before live conversion.

## Persistence and reference design
UUIDv5 is used only for repeatable fixtures in a dedicated PerchPoint namespace. Later production creation must issue stable server-controlled UUIDs. `ExternalReference` maps organization/integration/environment/provider-object identity to a canonical resource UUID. Provider strings never replace canonical keys.
Unit lease/ledger/document/utility/access workflows are future related records, not duplicate unit records per portal. This iteration defines contracts and relationships; it does not persist or execute those workflows.
Before PostgreSQL implementation, add foreign keys, composite organization constraints, uniqueness, relationship validity intervals, immutable history and tested RLS. Pydantic validation is not a database constraint.
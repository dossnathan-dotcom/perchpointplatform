"""One synthetic source of truth. UUIDv5 namespace and fixture labels are not provider IDs."""
from datetime import date, datetime, timezone
from uuid import UUID, uuid5

from .integrations import PROVIDER_TYPES, IntegrationRecord
from .people import PeopleGraph
from .property import Portfolio
from .reference import (
    InclusiveExclusiveDateRange,
    InclusiveExclusiveDateTimeRange,
    ManagementRelationship,
    OccupancyRelationship,
    OwnershipRelationship,
    PortfolioGroup,
    PortfolioMembership,
    HouseholdPortalAccess,
    PublishedListingRead,
    ReferenceSlice,
    SpaceOperatingState,
    project_phase0_unit_status,
)

NAMESPACE = UUID("4db53964-11d0-428e-b0b2-ef23f1c63e89")
NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)


def sid(name: str) -> UUID:
    return uuid5(NAMESPACE, name)


def money(amount: int):
    return {"amount_minor": amount * 100, "currency": "USD"}


def portfolio() -> Portfolio:
    org = sid("organization-demo")
    owner = sid("ownership-demo")
    client = sid("ownership-third-party")
    properties, buildings, units, spaces, assets = [], [], [], [], []
    configurations = [
        ("elm", "Example Elm Court", "mixed_use", [3], "mixedUse", "Cincinnati", "OH", "Hamilton", owner),
        ("duplex", "Example Clifton Duplex", "duplex", [2], "duplex", "Cincinnati", "OH", "Hamilton", owner),
        ("triplex", "Example Heritage Triplex", "triplex", [3], "triplex", "Cincinnati", "OH", "Hamilton", owner),
        ("house", "Example Garden House", "single_family", [1], "duplex", "Cincinnati", "OH", "Hamilton", owner),
        ("commercial", "Example Commerce Site", "commercial", [2], "storefront", "Covington", "KY", "Kenton", client),
        ("multifamily", "Example River Campus", "multifamily", [2, 2], "triplex", "Pittsburgh", "PA", "Allegheny", client),
    ]
    for key, name, kind, counts, image, city, state, county, ownership in configurations:
        prop_id = sid(f"property-{key}")
        properties.append({"id": prop_id, "organization_id": org, "ownership_entity_id": ownership, "name": name, "property_type": kind,
            "address": {"line1": f"EXAMPLE ONLY — {name} (not a deliverable address)", "country": "US", "state": state, "county": county, "municipality": city, "postal_code": "EXAMPLE", "is_example": True}})
        for bindex, count in enumerate(counts):
            bid = sid(f"building-{key}-{bindex}")
            uses = ["residential", "commercial"] if kind == "mixed_use" else ["commercial"] if kind == "commercial" else ["residential"]
            buildings.append({"id": bid, "organization_id": org, "property_id": prop_id, "name": f"Building {bindex + 1}", "allowed_uses": uses})
            for index in range(count):
                use = "commercial" if kind == "commercial" or (kind == "mixed_use" and index == 2) else "residential"
                label = "Bakery C1" if key == "elm" and index == 2 else f"{bindex+1}{chr(65+index)}"
                status = "occupied" if (index == 1 or label == "Bakery C1") else "available"
                terms = {"intended_use": "Bakery / retail" if label == "Bakery C1" else "Retail / office", "base_rent": money(3800), "rent_period": "month", "deposit": money(7600), "lease_type": "NNN — example only", "cam_nnn_terms": "Tenant share of CAM, taxes and insurance; amounts unapproved", "utility_responsibility": "Separately metered electric and gas; allocation pending review", "zoning_notes": "Intended use only; zoning and permits NOT verified", "loading_access": "Example rear service entry", "parking": "Example shared parking; allocation unverified", "build_out_status": "Illustrative food-service fit-out" if label == "Bakery C1" else "Illustrative shell condition"} if use == "commercial" else None
                residential = {"bedrooms": 1 if key == "triplex" else 2, "bathrooms": 1 if key in ("triplex", "duplex") else 2, "monthly_rent": money(1950 if key == "triplex" else 1650 if key == "duplex" else 2250), "security_deposit": money(1950 if key == "triplex" else 1650 if key == "duplex" else 2250), "application_fee": money(45), "utilities": "Example: separately metered gas/electric; water allocation pending approval", "pet_policy": "Example pet terms awaiting approval; no verified policy"} if use == "residential" else None
                units.append({"id": sid(f"unit-{key}-{bindex}-{index}"), "organization_id": org, "property_id": prop_id, "building_id": bid, "label": label, "use": use, "square_feet": 1850 if use == "commercial" else 840 if key == "triplex" else 1120, "status": status, "available_date": "2027-01-15" if status == "available" else None, "residential": residential, "commercial": terms, "image_key": "bakery" if label == "Bakery C1" else image})
            for skind in ["entry", "parking", "roof", "utility_room", "exterior"]:
                space_id = sid(f"space-{key}-{bindex}-{skind}")
                spaces.append({"id": space_id, "organization_id": org, "property_id": prop_id, "building_id": bid if skind not in ("parking", "exterior") else None, "name": f"Example {skind.replace('_', ' ')}", "kind": skind})
                if skind in ("roof", "entry", "utility_room"):
                    assets.append({"id": sid(f"asset-{key}-{bindex}-{skind}"), "organization_id": org, "property_id": prop_id, "building_id": bid, "shared_space_id": space_id, "name": {"roof": "Example HVAC system", "entry": "Example access control", "utility_room": "Example meter bank"}[skind], "kind": {"roof": "hvac", "entry": "access", "utility_room": "meter"}[skind]})
    return Portfolio.model_validate({"organizations":[{"id": org, "name": "HawkVision Homes — synthetic organization"}], "ownership_entities":[{"id": owner, "organization_id": org, "legal_name": "EXAMPLE ONLY — Demo Ownership LLC (fictional)", "entity_type": "llc", "management_relationship": "owned"}, {"id": client, "organization_id": org, "legal_name": "EXAMPLE ONLY — Demo Client Trust (fictional)", "entity_type": "trust", "management_relationship": "third_party_managed"}], "properties":properties, "buildings":buildings, "units":units, "shared_spaces":spaces, "assets":assets})


def people_graph(p: Portfolio) -> PeopleGraph:
    org = p.organizations[0].id
    names = ["Primary Resident Example", "Adult Co-signer Example", "Minor Occupant Example", "Applicant One Example", "Applicant Two Example", "Maintenance Employee Example", "Subcontractor Example", "Guarantor Example", "Emergency Contact Example"]
    people = [{"id": sid(f"person-{i}"), "display_name": name, "age_class": "minor" if i == 2 else "adult", "identity_status": "synthetic"} for i, name in enumerate(names)]
    account_indexes = [0, 1, 3, 4, 5, 6, 7]
    accounts = [{"id": sid(f"account-{i}"), "person_id": sid(f"person-{i}"), "status": "synthetic"} for i in account_indexes]
    households = [{"id": sid("household-resident"), "organization_id": org, "label": "Example resident household", "status": "resident"}, {"id": sid("household-applicant"), "organization_id": org, "label": "Example applicant household", "status": "applicant"}]
    relationships = []
    definitions = [(0,"primary_holder","resident"),(0,"resident","resident"),(1,"adult_signer","resident"),(2,"minor_occupant","resident"),(3,"applicant","applicant"),(4,"co_applicant","applicant"),(5,"maintenance_employee",None),(6,"subcontractor",None),(7,"guarantor","applicant"),(8,"emergency_contact","resident"),(0,"former_resident",None),(5,"staff",None),(6,"vendor_contact",None)]
    for i, kind, household in definitions:
        relationships.append({"id": sid(f"relationship-{i}-{kind}"), "person_id": sid(f"person-{i}"), "organization_id": org, "kind": kind, "household_id": sid(f"household-{household}") if household else None, "unit_id": p.units[1].id if household == "resident" else p.units[0].id if household else None, "account_id": sid(f"account-{i}") if i in account_indexes else None, "attributable_access_required": kind in ("adult_signer", "co_applicant", "applicant"), "effective_at": NOW, "ended_at": datetime(2026,10,1,tzinfo=timezone.utc) if kind == "former_resident" else None})
    business = {"id": sid("business-bakery"), "organization_id": org, "legal_name": "EXAMPLE ONLY — Synthetic Bakery LLC", "kind": "tenant"}
    relationships.append({"id": sid("business-tenant-contact"), "person_id": sid("person-1"), "organization_id": org, "kind": "business_tenant", "business_party_id": business["id"], "unit_id": p.units[2].id, "effective_at": NOW})
    return PeopleGraph.model_validate({"people":people, "accounts":accounts, "households":households, "businesses":[business], "relationships":relationships, "organization_ids":[org], "unit_organizations":{str(u.id):u.organization_id for u in p.units}})


def reference_slice() -> ReferenceSlice:
    """0.2.0 relationships and space states. Does not change Phase 0 portfolio identities."""
    graph = portfolio()
    people = people_graph(graph)
    org = graph.organizations[0].id
    isolation = sid("organization-isolation")
    isolation_entity = sid("entity-isolation")
    isolation_property = sid("property-isolation")
    opened = InclusiveExclusiveDateRange(effective_on=date(2020, 1, 1))
    ended = InclusiveExclusiveDateRange(effective_on=date(2018, 1, 1), ended_on=date(2020, 1, 1))
    active_at = InclusiveExclusiveDateTimeRange(effective_at=NOW)
    properties = {item.id: item for item in graph.properties}
    ownership = []
    management = []
    for item in graph.properties:
        ownership.append(OwnershipRelationship(id=sid(f"ownership-rel-{item.id}"), organization_id=org, legal_entity_id=item.ownership_entity_id, property_id=item.id, interval=opened))
        management.append(ManagementRelationship(id=sid(f"management-rel-{item.id}"), organization_id=org, manager_organization_id=org, property_id=item.id, interval=opened))
    elm = next(item for item in graph.properties if item.name.startswith("Example Elm Court"))
    ownership.append(OwnershipRelationship(id=sid("ownership-rel-elm-historical"), organization_id=org, legal_entity_id=elm.ownership_entity_id, property_id=elm.id, interval=ended, note="Synthetic prior interval; not a second current owner"))
    ownership.append(OwnershipRelationship(id=sid("ownership-rel-isolation"), organization_id=isolation, legal_entity_id=isolation_entity, property_id=isolation_property, interval=opened))
    group = PortfolioGroup(id=sid("group-cincinnati"), organization_id=org, label="Synthetic Cincinnati group")
    memberships = [
        PortfolioMembership(id=sid(f"membership-{item.id}"), organization_id=org, group_id=group.id, property_id=item.id, interval=opened)
        for item in graph.properties if item.address.state == "OH"
    ]
    household = people.households[0].id
    business = people.businesses[0].id
    occupancies = []
    states = []
    published = None
    for index, unit in enumerate(graph.units):
        projected = project_phase0_unit_status(unit.status)
        if published is None and unit.status == "available" and unit.use == "residential":
            projected["publication"] = "published"
            projected["publication_source"] = "explicit"
            projected["legal_restriction"] = "none"
            projected["legal_restriction_source"] = "explicit"
            projected["mapping_notes"] = [*projected["mapping_notes"], "Publication is an explicit reference-slice example, not a Phase 0 status fact"]
            published = unit
        states.append(SpaceOperatingState(id=sid(f"space-state-{index}"), organization_id=org, space_id=unit.id, **projected))
        if unit.status != "occupied":
            continue
        if unit.use == "commercial":
            occupancies.append(OccupancyRelationship(id=sid(f"occupancy-{index}"), organization_id=org, space_id=unit.id, business_party_id=business, interval=active_at))
        else:
            occupancies.append(OccupancyRelationship(id=sid(f"occupancy-{index}"), organization_id=org, space_id=unit.id, household_id=household, interval=active_at))
    assert published is not None and published.residential is not None
    listing = PublishedListingRead(
        listing_id=sid("listing-reference-published"),
        space_id=published.id,
        property_name=properties[published.property_id].name,
        label=published.label,
        use="residential",
        municipality=properties[published.property_id].address.municipality,
        state=properties[published.property_id].address.state,
        publication="published",
        availability="offerable",
        monthly_amount=published.residential.monthly_rent,
        available_date=date.fromisoformat(published.available_date) if published.available_date else None,
    )
    portal = HouseholdPortalAccess(
        id=sid("portal-primary-resident"),
        organization_id=org,
        household_id=household,
        person_id=sid("person-0"),
        account_id=sid("account-0"),
        kind="primary",
        interval=active_at,
        authorization_reason="Synthetic default primary portal account",
    )
    return ReferenceSlice(
        ownership=ownership,
        management=management,
        groups=[group],
        memberships=memberships,
        occupancies=occupancies,
        portal_access=[portal],
        space_states=states,
        published_listings=[listing],
        known_organization_ids=[org, isolation],
        known_property_ids=[*properties, isolation_property],
        known_space_ids=[unit.id for unit in graph.units],
        known_entity_ids=[entity.id for entity in graph.ownership_entities] + [isolation_entity],
        known_household_ids=[item.id for item in people.households],
        known_person_ids=[item.id for item in people.people],
        known_account_ids=[item.id for item in people.accounts],
    )


def integration_registry(p: Portfolio) -> list[IntegrationRecord]:
    return [IntegrationRecord(id=sid(f"integration-{kind}"), organization_id=p.organizations[0].id, provider_type=kind, provider_name="Unselected — disconnected mock", environment="synthetic", connection_status="disconnected", configuration_status="not_configured", credential_reference=None, supported_capabilities=[], required_webhooks=[f"{kind}.status_changed"], last_successful_sync=None, last_failure=None, retry_exception_state="disabled", data_ownership="HawkVision-controlled canonical records; provider objects are external mappings only", mapping_record_ids=[], activation_checklist=["Explicit later-phase approval", "Company-controlled account and recovery", "Capability and webhook contract tests", "Privacy/legal review", "Server auth and RLS verification"], deactivation_procedure=["Pause commands", "Drain/reconcile outstanding events", "Revoke credentials", "Archive mappings"], replacement_procedure=["Export canonical data", "Map new provider objects", "Reconcile control totals", "Approve cutover", "Retire prior provider"]) for kind in PROVIDER_TYPES]
"""One synthetic source of truth. UUIDv5 namespace and fixture labels are not provider IDs."""
from datetime import datetime, timezone
from uuid import UUID, uuid5

from .integrations import PROVIDER_TYPES, IntegrationRecord
from .people import PeopleGraph
from .property import Portfolio

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


def integration_registry(p: Portfolio) -> list[IntegrationRecord]:
    return [IntegrationRecord(id=sid(f"integration-{kind}"), organization_id=p.organizations[0].id, provider_type=kind, provider_name="Unselected — disconnected mock", environment="synthetic", connection_status="disconnected", configuration_status="not_configured", credential_reference=None, supported_capabilities=[], required_webhooks=[f"{kind}.status_changed"], last_successful_sync=None, last_failure=None, retry_exception_state="disabled", data_ownership="HawkVision-controlled canonical records; provider objects are external mappings only", mapping_record_ids=[], activation_checklist=["Explicit later-phase approval", "Company-controlled account and recovery", "Capability and webhook contract tests", "Privacy/legal review", "Server auth and RLS verification"], deactivation_procedure=["Pause commands", "Drain/reconcile outstanding events", "Revoke credentials", "Archive mappings"], replacement_procedure=["Export canonical data", "Map new provider objects", "Reconcile control totals", "Approve cutover", "Retire prior provider"]) for kind in PROVIDER_TYPES]
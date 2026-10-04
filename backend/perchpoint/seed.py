"""Synthetic seed. Runs as the local superuser because forced RLS blocks unscoped inserts."""
from __future__ import annotations

import uuid

import bcrypt
from sqlalchemy import text

from foundation.seeds import portfolio, sid

from .db import engine_for
from .phase6_policy import BUNDLES
from .settings import Settings


def seed(settings: Settings | None = None, database: str = "perchpoint_phase2") -> None:
    settings = settings or Settings.load()
    graph = portfolio()
    org = graph.organizations[0].id
    elm = next(item for item in graph.properties if item.id == sid("property-elm"))
    bakery = next(item for item in graph.units if item.id == sid("unit-elm-0-2"))
    residential = next(item for item in graph.units if item.property_id == elm.id and item.use == "residential")
    building = next(item for item in graph.buildings if item.id == residential.building_id)
    password_hash = bcrypt.hashpw(settings.dev_password.encode(), bcrypt.gensalt()).decode()
    admin = engine_for(settings.admin_url.rsplit("/", 1)[0] + "/" + database)
    with admin.begin() as connection:
        connection.execute(text("INSERT INTO organizations (id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING"), {"id": org, "name": "HawkVision Homes — synthetic organization"})
        connection.execute(text("INSERT INTO organizations (id, name) VALUES (:id, :name) ON CONFLICT (id) DO NOTHING"), {"id": sid("organization-isolation"), "name": "Synthetic isolation organization"})
        connection.execute(
            text("INSERT INTO legal_entities (organization_id, id, legal_name) VALUES (:org, :id, :name) ON CONFLICT (id) DO NOTHING"),
            {"org": org, "id": elm.ownership_entity_id, "name": "EXAMPLE ONLY — Demo Ownership LLC (fictional)"},
        )
        connection.execute(
            text(
                """
                INSERT INTO properties (organization_id, id, name, property_type)
                VALUES (:org, :id, :name, :kind) ON CONFLICT (id) DO NOTHING
                """
            ),
            {"org": org, "id": elm.id, "name": elm.name, "kind": elm.property_type},
        )
        connection.execute(
            text(
                """
                INSERT INTO buildings (organization_id, id, property_id, name, allowed_uses)
                VALUES (:org, :id, :property, :name, :uses) ON CONFLICT (id) DO NOTHING
                """
            ),
            {"org": org, "id": building.id, "property": elm.id, "name": building.name, "uses": list(building.allowed_uses)},
        )
        for unit in (residential, bakery):
            connection.execute(
                text(
                    """
                    INSERT INTO spaces (organization_id, id, property_id, building_id, label, use, square_feet)
                    VALUES (:org, :id, :property, :building, :label, :use, :area)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"org": org, "id": unit.id, "property": elm.id, "building": building.id, "label": unit.label, "use": unit.use, "area": unit.square_feet},
            )
            published = unit.id == residential.id
            connection.execute(
                text(
                    """
                    INSERT INTO space_states (
                      organization_id, id, space_id, condition, occupancy, availability, publication,
                      maintenance_restriction, legal_restriction, version, current
                    ) VALUES (
                      :org, :id, :space, 'rent_ready', 'vacant', 'offerable', :publication, 'none', 'none', 1, true
                    ) ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"org": org, "id": sid(f"seed-state-{unit.label}"), "space": unit.id, "publication": "published" if published else "unpublished"},
            )
        terms = residential.residential
        if terms is None:
            raise RuntimeError("The seeded residential space has no rent terms")
        rent = terms.monthly_rent
        connection.execute(
            text(
                """
                INSERT INTO listings (
                  organization_id, id, space_id, publication, availability, property_name, label, use,
                  municipality, state, amount_minor, currency
                ) VALUES (
                  :org, :id, :space, 'published', 'offerable', :property, :label, 'residential',
                  :city, :state, :amount, 'USD'
                ) ON CONFLICT (id) DO NOTHING
                """
            ),
            {
                "org": org,
                "id": sid("listing-reference-published"),
                "space": residential.id,
                "property": elm.name,
                "label": residential.label,
                "city": elm.address.municipality,
                "state": elm.address.state,
                "amount": rent.amount_minor,
            },
        )
        users = [
            ("nathan.synthetic@example.com", sid("account-phase2-nathan"), "platform_admin", org, None),
            ("ann.synthetic@example.com", sid("account-phase2-ann"), "leasing", org, None),
            ("resident.synthetic@example.com", sid("account-0"), "resident", org, None),
            ("isolation.synthetic@example.com", sid("account-phase2-isolation"), "platform_admin", sid("organization-isolation"), None),
            ("expired.synthetic@example.com", sid("account-phase2-expired"), "leasing", org, "2001-01-01T00:00:00Z"),
            ("faruk.synthetic@example.com", sid("account-phase6-faruk"), "owner", org, None),
            ("accounting.synthetic@example.com", sid("account-phase6-accounting"), "accounting", org, None),
            ("maintenance.synthetic@example.com", sid("account-phase6-maintenance"), "maintenance", org, None),
            ("vendor.admin.synthetic@example.com", sid("account-phase6-vendor-admin"), "vendor_admin", org, None),
            ("technician.synthetic@example.com", sid("account-phase6-technician"), "technician", org, None),
            ("cleaner.synthetic@example.com", sid("account-phase6-cleaner"), "cleaner", org, None),
            ("applicant.synthetic@example.com", sid("account-phase6-applicant"), "applicant", org, None),
            ("guarantor.synthetic@example.com", sid("account-phase6-guarantor"), "guarantor", org, None),
            ("former.synthetic@example.com", sid("account-phase6-former"), "resident", org, "2001-01-01T00:00:00Z"),
            ("suspended.synthetic@example.com", sid("account-phase6-suspended"), "leasing", org, None),
        ]
        for email, account_id, role, member_org, ended in users:
            connection.execute(
                text("INSERT INTO accounts (id, email, password_hash) VALUES (:id, :email, :password) ON CONFLICT (id) DO UPDATE SET password_hash = EXCLUDED.password_hash"),
                {"id": account_id, "email": email, "password": password_hash},
            )
            connection.execute(
                text(
                    """
                    INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at, ended_at)
                    VALUES (:id, :account, :org, :role, '1999-01-01T00:00:00Z', :ended)
                    ON CONFLICT (id) DO NOTHING
                    """
                ),
                {"id": sid(f"membership-{email}"), "account": account_id, "org": member_org, "role": role, "ended": ended},
            )
        connection.execute(
            text("INSERT INTO households (organization_id, id, label) VALUES (:org, :id, :label) ON CONFLICT (organization_id, id) DO NOTHING"),
            {"org": org, "id": sid("household-resident"), "label": "Example resident household"},
        )
        nathan = sid("account-phase2-nathan")
        connection.execute(
            text(
                """
                INSERT INTO memberships (id, account_id, organization_id, role_name, effective_at, ended_at)
                VALUES (:id, :account, :org, 'leasing', '1998-01-01T00:00:00Z', NULL)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": sid("membership-nathan-operations"), "account": nathan, "org": org},
        )
        codes = set().union(*BUNDLES.values()) | {"platform.secrets", "platform.database", "platform.deploy", "audit.delete", "listing.public", "inquiry.submit"}
        for code in sorted(codes):
            connection.execute(
                text("INSERT INTO capabilities (code, family, description) VALUES (:code, :family, :description) ON CONFLICT (code) DO NOTHING"),
                {"code": code, "family": code.split(".", 1)[0], "description": code},
            )
        for name, grants in BUNDLES.items():
            bundle = uuid.uuid5(uuid.NAMESPACE_URL, "perchpoint:role:" + name)
            connection.execute(
                text("INSERT INTO role_bundles (id, name, version) VALUES (:id, :name, 1) ON CONFLICT (id) DO NOTHING"),
                {"id": bundle, "name": name},
            )
            for capability in grants:
                connection.execute(
                    text("INSERT INTO role_bundle_capabilities (bundle_id, capability) VALUES (:bundle, :capability) ON CONFLICT DO NOTHING"),
                    {"bundle": bundle, "capability": capability},
                )
        connection.execute(
            text(
                """
                INSERT INTO service_principals (organization_id, id, name, status, interactive)
                VALUES (:org, :id, 'synthetic-worker', 'active', false)
                ON CONFLICT (organization_id, id) DO NOTHING
                """
            ),
            {"org": org, "id": sid("service-principal-worker")},
        )
    admin.dispose()


if __name__ == "__main__":
    seed()

# PerchPoint foundation refinement — contract version 0.1.0

Public company: **HawkVision Homes**. Public connection: **Powered by PerchPoint** / **Connected by PerchPoint**.
Internal: **PerchPoint — HawkVision Homes Property Operations**.

This is a controlled **Phase 0 foundation**, not production identity, authorization, money movement, screening, leasing, messaging or document storage.

## Documentation map
- [Scope, decisions and assumptions](SCOPE-AND-DECISIONS.md)
- [Canonical terminology and relationships](CANONICAL-MODEL.md)
- [Roles, permissions and access boundaries](ACCESS-CONTRACT.md)
- [Delegation model](DELEGATION.md)
- [Identity and MFA](IDENTITY.md)
- [Providers, screening and payments](INTEGRATIONS.md)
- [Data classification, documents, retention and jurisdictions](DATA-GOVERNANCE.md)
- [Migration and provenance](MIGRATION.md)
- [Audit, domain events and outbox/inbox](AUDIT-EVENTS.md)
- [Seed catalog and feature flags](SEEDS-AND-FLAGS.md)
- [Acceptance and verification](ACCEPTANCE.md)
- [Limitations and architectural review](LIMITATIONS.md)
- [Independent Cursor audit](../audits/PHASE_0_CURSOR_AUDIT.md)
- [Phase 1 governance and requirements](../governance/README.md)

## Source of truth
Executable Pydantic contracts: `backend/foundation/`. Derived JSON Schema: `contracts/generated/`.
Generated permission matrix: `contracts/generated/permission-matrix.csv` (all role/resource/action combinations, including explicit deny rows).
Generated fixtures: `contracts/fixtures/`. Frontend projection: `frontend/src/data/generated/foundation.json`.
Generated TypeScript: `frontend/src/contracts/generated.d.ts`. The browser and API use the same deterministic source.

```sh
cd /app/backend
python -m foundation.export
python -m foundation.export --check
cd /app/frontend
node scripts/generate-contract-types.cjs
node scripts/generate-contract-types.cjs --check
```

Do not edit generated files. The Python exporter regenerates fixtures and schemas without database writes. The TypeScript generator derives types from those JSON Schemas.

## Architecture
React/CRA/CRACO public site and role-specific preview routes; FastAPI read-only foundation metadata; existing MongoDB synthetic inquiry and maintenance capture. No canonical production persistence is introduced. Existing environment keys are preserved.
PostgreSQL is a **future production enforcement target**, not an installed or verified database in this iteration. Server authorization and RLS require explicit later approval, database design, and direct integration tests.

The independent Cursor audit is later evidence and does not rewrite this historical Phase 0
record. Where fresh execution differs from retained claims, the audit verdict controls current
acceptance.

## Routes
- `/`: public rental/property-operations site.
- `/rentals/:unitId`: unit-specific terms using PerchPoint UUIDs. `/property/:propertyId` is a legacy path alias for a UUID, not a separate model.
- `/perchpoint`: explicit role-preview gate; no password inputs.
- `/perchpoint/:roleId/:viewId?`: eight role shells with real navigation between different preview views.
- `/foundation/:sectionId?`: overview, permissions, delegation, providers, migration, identity/retention, scenarios.
- `GET /api/properties`: canonical property records, **not rental units**.
- `GET /api/rentals`: canonical unit records with residential/commercial-specific terms.
- `GET /api/foundation`, `/api/foundation/portfolio`, `/api/foundation/contracts`: read-only synthetic contract metadata.
- `POST /api/leads`, `/api/maintenance-requests`: retained synthetic capture only; no external side effects.

The historical slug-based listing URLs are not canonical IDs and show an unavailable state. No production inventory was migrated from the former brokerage model.
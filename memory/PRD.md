# PerchPoint by HawkVision Homes — Product Requirements

## Product Identity

**PerchPoint** is the property operations platform by **HawkVision Homes**.

- Public brand: HawkVision Homes
- Operating system: PerchPoint
- Internal subtitle: HawkVision Homes Property Operations
- Resident language: Your PerchPoint Resident Portal
- Initial market: Greater Cincinnati, with a model that can expand to other municipalities and states

## Governing Product Direction

The original HawkVision prototype was visually strong but incorrectly positioned as a luxury home-sales brokerage. The product has been repositioned as a rental and property-operations platform while preserving its charcoal foundation, burnt-copper accent, premium typography, Cincinnati imagery, refined spacing, and high-trust presentation.

The active direction is:

- Build iteratively internally and present comprehensively externally.
- Use internal release gates without presenting incomplete client deliverables.
- Avoid deep production functionality until Phase 0 legal, identity, payment, screening, data-retention, and operating contracts are finalized.
- Clearly label seeded rental, portal, financial, and performance information as demonstration data.
- Do not reintroduce AI/chat unless explicitly requested.

## Primary Users

### Public and household users
- Prospective residential renter
- Prospective commercial tenant
- Applicant
- Primary resident household account holder
- Adult co-tenant who needs attributable signatures, notices, consent, or document access

### Business and operating users
- Farouk — Owner / Asset Principal
- Nathan — Platform Super Administrator
- Leasing / Project Manager
- Accounting contractor
- Maintenance employee
- Subcontractor

## Core Public Requirements

- Available residential, commercial, and mixed-use rentals
- Cincinnati-area neighborhood context
- Clear monthly rent, deposits, fees, utility responsibility, pet terms, and qualification guidance
- Showing scheduling
- Application initiation
- Resident resources
- Non-emergency maintenance reporting
- High-visibility emergency-maintenance instructions
- HawkVision property-management standards
- No fictional principals, advisors, testimonials, transaction claims, or unlabeled statistics
- Public header emphasizes HawkVision Homes; sign-in directs users to PerchPoint

## Property Domain Model

```text
Organization
└── Ownership entity
    └── Property
        ├── Building
        │   └── Unit
        └── Shared spaces/assets
```

Supported property shapes:

- Single-family houses
- Duplexes
- Triplexes
- Larger multifamily properties
- Commercial properties
- Mixed-use properties
- Buildings with both residential and commercial units

Each unit is intended to maintain independent leases, occupants, rent, ledger, documents, maintenance, utilities, and access instructions.

## Household Identity Contract

- One resident is the primary household account holder.
- Other occupants may be listed without full accounts.
- Adults receive individual accounts when signatures, regulated consent, notices, or document access require attribution.
- Household members never share one password.

## Role and Access Contract

### Farouk — Owner
Can access all business operations, properties, units, residents, applicants, maintenance, financials, vendors, documents, communications, reserved approvals, business policies, delegations, audits, and performance reporting.

Does not automatically receive database administration, production secrets, source code, deployment controls, migrations, row-level security policy changes, audit deletion, developer feature flags, or integration-secret rotation.

### Nathan — Platform Super Administrator
Owns application configuration, integrations, security, development controls, infrastructure, role-policy implementation, and protected technical administration.

### Leasing / Project Manager
Portfolio-wide applicant, showing, leasing, communication, turnover, and maintenance-coordination visibility.

### Accounting contractor
Financial reconciliation, unit ledgers, approved documents, vendor invoices, and property reporting.

### Maintenance employee
Assigned work, required property/resident context, access instructions, estimates, evidence, and schedules.

### Subcontractor
Assigned jobs only, necessary access details, job communication, estimates, evidence, and invoices.

### Primary resident
Household lease, balance, payments, documents, communication, access information, and maintenance.

### Applicant
Only their application, documents, screening consent, status, communication, and lease process.

Sensitive screening and identity access must eventually create a reasoned, timestamped audit event.

## Delegation Policy Contract

Approvals must support combinations of:

- Dollar amount
- Property and unit
- Expense category and decision type
- Budget availability
- Tenant monthly rent
- Emergency status
- Requesting employee and vendor
- Time period and active delegation
- Prior spending on the same issue

Reserved owner authority includes final applicant approval, lease approval, legal matters, spending outside policy, and repair totals above configurable rules. Emergency authority may act to protect life or property but requires immediate notification and retrospective review. Exact thresholds remain configurable until Farouk approves them.

## Implemented — 2026-09-21

### Public experience
- Rebranded the product as PerchPoint by HawkVision Homes.
- Rebuilt navigation around rentals, properties, applications, resident resources, maintenance, company approach, and PerchPoint sign-in.
- Preserved the cinematic Cincinnati hero and kinetic heading transitions with rental/property-operations messaging.
- Added seeded residential, commercial, duplex, triplex, and mixed-use rental cards.
- Added transparent example rent, deposit, utility, pet, application, and qualification terms.
- Added rental-type filtering and complete rental detail routes.
- Added showing requests and application-interest capture through `POST /api/leads`.
- Added a property hierarchy explorer with organization, ownership entity, property, building, residential units, commercial unit, and shared assets.
- Added a four-step application explanation.
- Added resident resources, household identity guidance, emergency instructions, and non-emergency maintenance reporting.
- Added HawkVision operating standards without fictional staff profiles or testimonials.
- Added responsive public navigation and mobile layouts.

### PerchPoint operating shell
- Added eight seeded role previews: Owner, Platform Super Administrator, Leasing, Accounting, Maintenance, Subcontractor, Primary Resident, and Applicant.
- Added role-specific workspace navigation, metrics, queues, access boundaries, and responsive internal layouts.
- Added visible separation between owner business authority and super-administrator infrastructure authority.
- Added a multidimensional delegation-policy matrix preview for Owner and Platform Super Administrator roles.
- Added explicit Phase 0 and demonstration-data disclosures.
- Removed all sales-era buyer, seller, valuation, saved-home, luxury advisor, buyer quiz, and testimonial modules.

### Backend
- Renamed the API service to PerchPoint.
- Replaced sales inventory with seeded rental/unit records at `GET /api/properties`.
- Retained inquiry capture at `POST /api/leads` for showing, application-interest, and contact requests.
- Added `POST /api/maintenance-requests` with validation and MongoDB persistence.
- Uses `MONGO_URL`, `DB_NAME`, and `CORS_ORIGINS` from the backend environment.

## Current Authentication Status

**MOCKED:** all eight role profiles are frontend-only seeded demonstrations. No production authentication, authorization enforcement, MFA, password storage, refresh tokens, screening access, or protected financial access is active.

Production JWT/session implementation is intentionally deferred until Phase 0 identity, MFA, audit, retention, and authorization contracts are approved. Current test credentials are documented in `/app/memory/test_credentials.md`.

## Verification

- Production frontend build passes.
- Backend Python compilation passes.
- Automated backend suite passes 6/6 tests.
- `GET /api/health` returns the PerchPoint service.
- `GET /api/properties` returns seeded Phase 0 rental data.
- Showing and application-interest requests persist through `POST /api/leads`.
- Maintenance requests persist through `POST /api/maintenance-requests`.
- Browser testing passed public copy guards, navigation, responsive behavior, filters, details, map, request flows, hierarchy, resident resources, owner login, all eight role shells, delegation access, and mobile overflow checks.
- Full report: `/app/test_reports/iteration_1.json`.

## Prioritized Roadmap

### P0 — Phase 0 contracts and source-of-truth decisions
1. Confirm HawkVision legal entity, property ownership entities, verified properties, units, addresses, rents, deposits, fees, utility allocations, pet policies, and qualification criteria.
2. Approve role-permission matrix, reserved decisions, delegation dimensions, initial thresholds, emergency authority, and audit requirements.
3. Approve household identity, co-tenant, screening-data, identity-document, notice, signature, and retention rules.
4. Confirm company-controlled domain, technical address, MFA recovery ownership, password manager, billing ownership, and account-provisioning checklist.
5. Select production identity, payment, screening, document storage/signature, messaging, and accounting integrations only when required.

### P1 — Internal vertical releases
1. Persist organization, ownership entity, property, building, unit, shared asset, household, lease, and occupant models.
2. Implement production authentication, MFA, session handling, RBAC/policy enforcement, and immutable sensitive-access events.
3. Build applicant intake, consent, document collection, screening handoff, approval, lease preparation, and status workflow.
4. Build resident ledger, payments, documents, notices, household access, and maintenance lifecycle.
5. Build work orders, vendor assignments, estimates, evidence, invoices, budgets, approvals, and delegation enforcement.
6. Build accounting reconciliation and property/unit reporting.

### P2 — External readiness and growth
1. Replace all seeded rental data with verified HawkVision inventory and approved imagery.
2. Add real tenant and business testimonials only after written approval.
3. Add production notifications, analytics, audit exports, accessibility verification, SEO, and performance monitoring.
4. Expand jurisdiction-aware configuration for additional municipalities and states.

## Immediate Next Action

Finalize the Phase 0 source-of-truth contracts before converting any seeded portal shell into production identity, financial, screening, payment, or legally attributable workflow functionality.
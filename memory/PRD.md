# HawkVision Homes / PerchPoint — Current Product Requirements

## Identity and original direction
HawkVision Homes is a rental and property-operations company for residential, commercial and mixed-use real estate. PerchPoint is its operating platform.
- Public: **HawkVision Homes**, **Powered by PerchPoint** / **Connected by PerchPoint**.
- Internal: **PerchPoint — HawkVision Homes Property Operations**.
- Initial operating region: Greater Cincinnati. No schema or policy assumes Ohio is the only jurisdiction.
- Approved premium design: charcoal/black, warm copper-orange, Playfair Display / IBM Plex Sans, Cincinnati imagery, generous public spacing, denser internal operations.
- No buyer/seller brokerage, valuation, private-portfolio positioning, fictional testimonials/history/advisors/statistics, or reintroduced AI/chat.

## Active user request and governing boundary
Latest request: **narrow Phase 0 remediation only** for seeded role navigation (URL changed while gate/modal appeared stale), all-eight-role history/direct/nested navigation checks, four public synthetic API boundaries, and exact regression evidence. No features, schema expansion, visual redesign or later-phase work. Stop after remediation and await review.

The user requested a **controlled Phase 0 foundation refinement**, not production screening, payment processing, lease execution, authentication, messaging, Twilio routing, document storage or tenant-account creation. Preserve public IA and the premium design, refine accessibility/content, implement canonical schemas and synthetic scenarios, formalize access/delegation/identity/integration/migration/audit/retention/jurisdiction contracts, create actual role-preview shells, document and verify everything. Do not automatically move to a later phase.

Public IA: Available Rentals, Properties, How to Apply, Resident Resources, Maintenance, About, Contact HawkVision, Sign in to PerchPoint.

## Current architecture
- React 19 / CRA / CRACO / Tailwind / Shadcn UI, React Router. Legacy JSX remains JavaScript; generated TypeScript contracts and typed API boundary added.
- FastAPI / Pydantic v2 contracts in `backend/foundation/`.
- Existing MongoDB retains only synthetic inquiry and maintenance captures; canonical models remain validated fixtures, not production persistence.
- Required configuration: `REACT_APP_BACKEND_URL`; backend `MONGO_URL`, `DB_NAME`, `CORS_ORIGINS`. Protected values unchanged.
- Required new flags: frontend `REACT_APP_SHOW_DEMO_LABELS`, `REACT_APP_ENABLE_SEEDED_PREVIEWS`; backend `PHASE0_ENABLED`.
- Future PostgreSQL row-level security and server authorization are documented requirements, **not implemented or tested production controls**.
- Stable PerchPoint UUIDs; provider IDs only in external-reference records. One graph for all role shells, no portal-specific databases.

## Canonical real-estate model
Organization → OwnershipEntity → Property → Building → Unit.
SharedSpace belongs to property/building; Asset belongs to property/building/unit/shared location as appropriate.

Definitions and constraints are executable in `property.py`: same-org ownership, valid property/building/unit links, exclusive residential/commercial terms, allowed use, unique IDs, appropriate shared/asset links, complete single-family/duplex/triplex shapes. Multi-building and third-party-managed properties supported.

Residential terms: beds, baths, area, monthly rent, deposit, application fee, availability, utilities, pets.
Commercial terms: intended use, area, base rent/period, deposit, lease type, CAM/NNN, utilities, zoning/use notes, loading/access, parking, build-out, available date. No residential fields shown on commercial units.

## Person and household model
Person, UserAccount, Household, BusinessParty and time-bounded PersonRelationship are distinct.
Relationships include applicant/co-applicant, primary holder, adult signer, occupant/minor, guarantor, resident/former resident, business applicant/tenant, emergency contact, staff, maintenance employee, subcontractor/vendor contact.
One active primary holder per household. Adult signers/attributable access retain individual account references. Occupants need not have accounts. No passwords shared. Multiple historical relationships reuse one person.

## Phase 0 roles and boundaries
1. Farouk — Owner / Asset Principal: broad business access, owner-reserved applicant/lease/legal approvals; no automatic infrastructure/secrets/database/deployment/migration/RLS/developer controls or audit deletion.
2. Nathan — Platform Super Administrator: technical/configuration/integration/security/environment/development contracts; separate business/support purpose; no unrestricted impersonation.
3. Leasing / Project Manager: portfolio operations, tenants/applicants/showings/leasing/communication/maintenance, not unrestricted screening, financial adjustment or owner authority.
4. Accounting Contractor: authorized financial/reconciliation/reporting/document records, relationship-restricted.
5. Maintenance Employee: assigned work and necessary context.
6. Subcontractor: one seeded assignment only, no broad resident/applicant/financial/portfolio visibility.
7. Primary Resident: household records only, individual restricted records protected conceptually.
8. Applicant: own application/household relationships and allowed disclosures.

Future inventory: leasing agent, property manager, maintenance coordinator, vendor administrator, auditor, legal/compliance reviewer, additional household signer. No implicit grants.

## Implemented — 2026-09-21 refinement
### Public experience
- Stronger readable header/hero/body/eyebrow/button palette; carousel pause and reduced-motion behavior; stable slide composition.
- Correct singular/plural unit grammar and separate commercial terms.
- Functional location/use search and filters; canonical UUID unit detail routes; six-property selector and actual building/unit/shared-space/asset hierarchy.
- All addresses and entities explicitly fictional. Illustrative photography is not claimed to depict verified units.
- Feature flags suppress seeded surfaces when labels are removed; no unlabeled synthetic availability.
- Mobile navigation, safe modal bounds, explicit form labels, visible focus and unique interactive test IDs.
- Synthetic-only intake with reserved example email domains and truthful “no notification/dispatch/application created” confirmations.
- Page title and metadata now identify HawkVision / PerchPoint.

### Meaningful role shells
- Owner Command Center; Platform Administration; Leasing Operations; Accounting; Maintenance Operations; Subcontractor Assignments; Resident Portal; Applicant Portal.
- Deep role/view routes, navigation, scoped search/context, notification/account menus, record preview modals, disabled later-phase actions, empty/loading/error/denied state previews.
- Leasing Operations Console includes operational inbox, pipeline, showing/application queues, tenant directory, maintenance coordination, payment exceptions, approvals, documents/expirations, tasks, communication and system exceptions.
- Removed fake password authentication. Explicit role selector opens a real preview shell. No real accounts or credentials.

### Foundation implementation
- 59 JSON Schemas and generated TypeScript definitions; 67 deterministic schema/fixture/matrix artifacts from the Python source.
- 5,624 versioned deny/conditional-grant matrix rows: 8 roles × 37 resources × 19 actions.
- Pure permission/delegation evaluators: simulated outcomes only, no production authority or execution.
- Configurable seeded $250 staff/$500 parts/1× rent policies pending Farouk. Scope/expiry/value/self-approval/material revision/policy/concurrency context guards and emergency review flags.
- 18 identity lifecycle contracts, 10 disconnected provider types, payment/screening/document/retention/jurisdiction/audit/event/outbox/inbox/migration contracts.
- Synthetic portfolio: 1 organization, 2 ownership entities, 6 properties, 7 buildings, 15 units, 35 shared spaces, 21 assets across OH/KY/PA. Multi-building and fictional bakery included.
- 9 people, 7 synthetic account references, 2 households, business tenant and historical relationships.
- Synthetic Innago staging: 5 rows = 1 valid, 1 duplicate, 2 invalid, 1 canonical conflict; reconciliation review and zero writes.
- Comprehensive repository docs under `docs/phase0/`; old design guidance replaced to remove contradictory policies and fake biographies.

## Routes
- `/`, `/rentals/:unitId`; legacy `/property/:propertyId` accepts a canonical unit UUID, old slugs show unavailable.
- `/perchpoint` preview selection; `/perchpoint/:roleId/:viewId?` eight shells.
- `/foundation/:sectionId?` contract review surface.
- GET `/api/health`, `/api/properties` (actual property records), `/api/rentals` (unit records).
- GET `/api/foundation`, `/api/foundation/portfolio`, `/api/foundation/contracts` read-only fixtures.
- POST `/api/leads`, `/api/maintenance-requests` retained synthetic capture. No auth/provider execution endpoints.

## Verification and evidence
### Latest remediation verification — independent iteration 4
- Original indefinite leasing-gate stall did not reproduce in the current environment; no unique race/animation cause is claimed. Found and corrected route-independent modal ownership, reused portal descendant state, and missing invalid-view/path handling.
- One stable Routes tree; one location-key-scoped modal closed before navigate; portal subtree keyed by history entry; controlled unknown role/view/excess path. No forced reloads, timers or router downgrade.
- All eight roles independently passed entry without refresh, modal close, correct route/render, direct/refresh, back/forward, switching, stale-state clearance and nested navigation.
- Four public APIs remain deterministic synthetic builders only. Added no-store/phase0 headers, explicit public fixture documentation and fail-closed contamination rejection. Missing/invalid flags also disable preview data. No production source or authorization introduced.
- Final independent results: **20 routing tests + 2 flags tests passed; 52 backend tests passed (6 non-blocking deprecation warnings)**. Full Ruff/root+frontend ESLint, Mypy15files, TypeScript/build, 67-artifact repeatability and actual generated-TypeScript repeatability passed.
- Test-only CRA/Jest resolver/jsdom setup fixed the initial routing-test bootstrap blocker. Existing test imports cleaned; no assertions weakened.
- Reports: `test_reports/iteration_3.json` (initial automation failures retained), `test_reports/iteration_4.json` (final pass), `test_reports/routing-remediation/{navigation-matrix,api-matrix}.json`.
- Exact changed files, root-cause limits, commands/results and remaining warnings: `docs/phase0/ROUTING-REMEDIATION.md`. Phase 0 verification report updated.
- No environments, credentials, schema sources, seed sources, styling, dependencies or later-phase workflows changed. Public synthetic fixture guards are NOT a production serializer/auth/PII-security boundary.

### Previous foundation refinement evidence (historical)
- Final backend pytest: **26 passed in 1.68s**.
- Frontend Jest: **2 passed**, one suite.
- Frontend optimized build succeeds; ESLint, Ruff, Python compilation, TypeScript boundary checks pass.
- Mypy: no issues in 14 foundation source files.
- 59 generated schemas valid Draft 2020-12; 67 fixture/schema artifacts repeat exactly; TypeScript regeneration matches.
- Disabled backend flags tested: empty feeds, 404 foundation, 503 intake, no writes. Frontend flags tested for suppressing seed surfaces and missing/invalid config rejection.
- Testing agent reports public responsiveness at 320/768/1024/1440, mobile/hero/filter/detail/hierarchy/forms, all eight role routes/tabs, state previews, foundation sections/fallback and interactive-ID checks passed.
- Initial serious footer contrast failure fixed. Retest: zero axe violations on all three homepage slides, leasing, resident and foundation permissions.
- One automated homepage accessibility rule remains incomplete; manual photograph/assistive-tech/zoom review is still a publication gate. No WCAG certification claim.
- Evidence: `test_reports/iteration_2.json`, `test_reports/foundation/`, `docs/phase0/VERIFICATION.md`.
- Final metadata rebuild and backend compilation/export checks passed. Local environment files are ignored and untracked; protected configuration remains unchanged.
- Handoff lint-gate correction: added root `eslint.config.cjs` forwarding the same frontend rules; both system and project ESLint pass from `/app` as well as the frontend directory. No rules weakened.
- Measured essential contrast pairs: 5.42:1 copper/linen, 9.93:1 light copper/charcoal, 17.85:1 body/charcoal, 12.24:1 muted/charcoal, 7.91:1 footer-region label. Complete changed-file list: `docs/phase0/CHANGED-FILES.md`.

## Important limitations — explicit, not hidden
**MOCKED** role previews, provider adapters and queues. No production auth, MFA, authorization, PostgreSQL/RLS, financial ledger posting, money movement, screening/decisions/adverse action, lease signing, messaging or file storage. No durable policy/approval/audit/outbox/rollback enforcement. No automatic PII detection in free-text demo fields. No verified property inventory or approved legal policy.
Frozen models/checksums do not provide immutable storage. Future transactions must enforce approvals, audit and outbox atomically. Legacy JSX is built/linted, not fully statically typed.

## Prioritized remaining work
### P0 — Farouk and qualified review, not more production code
1. Review this foundation and the unchanged Phase 0 boundary.
2. Approve real company/entity/property/unit data, imagery and terms before replacing any seeds.
3. Approve role matrix, owner-reserved decisions, delegation dimensions/thresholds and emergency authority.
4. Approve identity/MFA/recovery/session/termination contracts and company account ownership.
5. Obtain qualified legal review for jurisdiction policies, disclosures/screening/adverse-action, deposit/fees/notices, retention and legal holds.
6. Cursor/Nathan review: PostgreSQL target, foreign keys/RLS, temporal person identity, atomic ledger/approval/audit/outbox, migration/currency/reconciliation/cutover strategy.
7. Complete human accessibility review of image-composited text, assistive technology and zoom.

### P1 — Deferred; explicit new authorization required
Canonical persistence and DB migrations; real auth/MFA/RLS; applicant screening/human decisions; resident ledger/payments; documents/signatures; work-order/vendor lifecycle; approvals and notifications; durable audits/outbox; validated Innago import and retirement.

### P2 — Deferred
Verified published inventory, approved analytics/notifications, multi-jurisdiction live policy rollout, company-controlled provider activation and evidence-based cutover.

## Next action
Stop and await user review of `docs/phase0/ROUTING-REMEDIATION.md`. Do not begin additional features, lifecycle cleanups or another phase. Existing Farouk/legal/architecture approvals remain deferred review items, not permission for implementation.
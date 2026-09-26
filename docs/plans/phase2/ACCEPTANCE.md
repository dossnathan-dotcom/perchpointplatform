# Phase 2 Acceptance Matrix

Classification: planning. Unrun tests are planned or blocked, never passed.

## Provisional quality targets

These are planning ceilings, not measured results (OD-011).

| Target | Planning value | Future measurement |
|---|---|---|
| Scale | At least 10× current ~100-property / 100-tenant planning base | Declared synthetic benchmark |
| Availability | 99.9% core | Later SLO on authenticated command/read success, excluding planned maintenance |
| Ordinary read p95 | < 500 ms | Same region, warm DB, authorized list/detail |
| Material command p95 | < 1 s excluding providers | `SubmitInquiry` / `TriageInquiry` |
| Typical search | < 1 s | Scoped inquiry/activity search |
| Dashboard useful content | < 2 s | Staff triage queue first paint with data |
| Accessibility | WCAG 2.2 AA critical journeys | Keyboard, focus, contrast, plus axe as evidence not certification |
| Browsers | Current and previous major desktop; modern mobile | Manual + Playwright later |
| Width | Responsive from ~320 px | Existing public layouts plus new persistent views |
| Drafts / retry | Recoverable drafts; no unrestricted sensitive offline replica | Command idempotency + UI retry |
| Observability | Correlated, redacted, role-appropriate alerts | Later; Phase 2 proves redaction tests |

Transaction durability is not disaster recovery. Provisional general-data
planning ceiling: RPO 24 hours, RTO 4 hours. Financial/audit recovery needs a
tighter later objective and PITR/restore evidence. An ACID commit does not
imply near-zero disaster loss.

## Initial benchmark design (synthetic)

Assumptions, not portfolio facts:

- 1,000 properties
- 3,000 spaces
- 5,000 people
- 25,000 inquiries
- 250,000 activity/audit rows
- 25 concurrent mixed users (public listing, staff triage, resident-denied)

Record hardware, workload mix, warm versus cold, error rates, p50/p95/p99,
and query plans. Refine after first measurement. Do not run this benchmark
during planning.

## Measurement 2026-09-24

The design mix in "Initial benchmark design (synthetic)" was loaded into
disposable database `perchpoint_phase2_bench`, migrated to
`0006_activity_index`, measured, and dropped. PostgreSQL 16.15. Runtime role
`perchpoint_runtime` (`NOSUPERUSER`, `NOBYPASSRLS`) with transaction-local
`app.actor_id`, `app.organization_id`, and `app.request_id`. Households are
the persisted person records in migration `0001`; there is no separate people
table. Warmup: 1. Measured runs: 10. Each sample is one target statement plus
one `set_config`. No ORM N+1 loop. Concurrency: 25 separate runtime
connections after one warmup wave of 25. No errors or timeouts.

| Cardinality | Count |
|---|---:|
| Properties | 1,000 |
| Buildings | 1,000 |
| Spaces | 3,000 |
| Households | 5,000 |
| Listings | 1,000 |
| Inquiries | 25,000 |
| Activity rows | 250,000 |
| Organizations | 2 |
| Active memberships | 2 |
| Expired memberships | 1 |

| Query | p50 ms | p95 ms | max ms | Plan evidence |
|---|---:|---:|---:|---|
| Property list, 50 rows | 5.41 | 5.50 | 5.55 | Bitmap index scan on `properties_pkey`, 500 visible rows, 4.688 ms |
| Property hierarchy | 14.19 | 14.39 | 14.56 | Bitmap index scans on `buildings_pkey` and `spaces_pkey`, 13.603 ms |
| Inquiry queue, 50 rows | 135.27 | 137.51 | 138.90 | Sequential scan, 12,500 visible rows, 138.096 ms |
| Inquiry detail | 0.72 | 0.77 | 0.84 | Primary-key index scan, 0.096 ms |
| Activity timeline, 50 rows | 3.19 | 3.42 | 3.43 | Bitmap index scan on `activity_resource_time`, 250 rows, 2.613 ms |
| Public published listings | 0.98 | 1.11 | 1.14 | Function scan, 333 rows, 0.280 ms |
| Public listing detail | 0.81 | 0.84 | 0.86 | Function scan, 1 row, 0.389 ms |
| RLS property count, other organization | 5.25 | 5.54 | 5.67 | Bitmap index scan, 500 rows of that organization, 4.529 ms |
| Concurrent public listings, 25 connections | 15.94 | 40.23 | 169.56 | Separate runtime connections |
| Concurrent internal property list, 25 connections | 17.10 | 20.28 | 21.76 | Separate runtime connections |

Organization A saw 500 of 1,000 properties. All measured reads are under the
500 ms ordinary-read ceiling. The inquiry queue stays a sequential scan at
this size; no additional index was added. The hierarchy plan filters by
organization index rather than issuing one query per building.

After `DROP DATABASE`, `perchpoint_phase2_bench` was gone. Development
database `perchpoint_phase2` still had Elm Court (`9960c7ea-3d4b-5fd7-90b3-6360439a6875`)
once, zero properties named `Bench`, and migration head `0006_activity_index`.

## Required evidence (P2-01 through P2-05)

| Evidence | Package | Planned command / method | Status now |
|---|---|---|---|
| Contract generation and compatibility | P2-01 | `python -m foundation.export --check`; TS `--check` | passed: 107 artifacts, generated TypeScript matches |
| Clean and upgrade migrations | P2-02 | empty database upgrade through head | passed through `0006_activity_index`; no revision exists before `0001` |
| Organization-aware constraints | P2-02 | constraint pytest as runtime role | passed in the 79-test backend run |
| Direct DB + API authorization | P2-02 | runtime-role and API denial tests | passed, including expired membership and cross-organization denial |
| Actor and pooled-context isolation | P2-02 | two-checkout leak test | passed |
| Atomic domain/audit/outbox/idempotency | P2-03 | command runner tests | passed, including injected rollback |
| Concurrent retries and stale edits | P2-03 | threaded pytest and UI 409 | passed in pytest; Playwright confirms the stale-edit message |
| Worker crash recovery | P2-03 | lease-expiry reclaim test | passed |
| Fake webhook authenticity, dedupe, order | P2-03 | inbox tests | passed |
| Redaction and scoped projections | P2-03 / P2-04 | public GET tests | passed: public listing omits organization and space identifiers |
| Historical relationship correctness | P2-01 / P2-02 | effective-dated fixtures | passed for active and expired memberships; not a full tenancy history |
| Browser journeys and accessibility | P2-04 / P2-05 | `corepack yarn playwright test --reporter=line` | passed: 15 tests, 0 failed, 0 skipped, 40.8 s, exit 0 |
| Measured performance | P2-05 | disposable design-mix benchmark | passed: every measured read p95 is below 500 ms |
| Existing Phase 0/1 regression gates | P2-05 | established suite | frontend unit tests 22 passed; production build compiled |

## Changed-UI journey matrix

Every changed persistent journey must demonstrate:

loading, empty, invalid, denied, missing, stale-version, transient-failure,
retry, and successful persistence.

Journeys in scope:

1. Public published listing (320 px and desktop).
2. Staff property → building → space.
3. Submit synthetic inquiry (authenticated local actor).
4. Staff triage with activity history.
5. Denied cross-org and cross-household reads.
6. Preview role cannot write persistent commands.

## Stop conditions

- Required PostgreSQL evidence replaced by SQLite or in-memory claims.
- Required test skipped and reported passed.
- Live provider, real PII, or production credential introduced.
- Emergent or Cursor edits canonical schemas outside the freeze process.
- `/app` hardcoded as repository root.
- Phase 2 presented as production-ready.

## Closure evidence 2026-09-24

Playwright command, from `frontend/`: `corepack yarn playwright test --reporter=line`.
Result: 15 passed, 0 failed, 0 skipped, 40.8 seconds, exit 0. That single
process includes the public listing and inquiry, idempotent retry, property,
building, space, offerability, listing publication, public appearance, stale
409, inquiry assignment, triage, internal note, activity timeline,
authorization boundaries, organization isolation, keyboard submission and
assign, axe critical/serious/moderate on `/` and the signed-in platform
workspace, and overflow checks at 320, 768, 1024, and 1440 px.

Phase 2 workflows do not use a modal or dialog. Inspected
`frontend/src/components/portal/Phase2Kernel.jsx`,
`frontend/src/components/Listings.jsx`, and
`frontend/src/components/PropertyDetailPage.jsx`. Focus entry, containment,
Escape, and restoration are non-applicable for those workflows. Phase 0
preview dialogs remain outside this command path. A screen-reader pass was
not performed, and this is not a WCAG certification.

Consolidated checks after the final benchmark and browser edits: source
verification passed; governance reported 71 requirements and 58 decisions;
`python -m foundation.export --check` reported 107 artifacts; pytest 79
passed, 0 failed, 0 skipped, exit 0; Ruff and Mypy passed; frontend frozen
install, contract types, TypeScript, ESLint, 22 unit tests, and production
build passed. Twenty application tables have forced row-level security.
`alembic_version` is the remaining public table and is not tenant data.
`perchpoint_runtime` is not a superuser and does not bypass row-level security.

| Package | Status |
|---|---|
| P2-01 | passed |
| P2-02 | passed |
| P2-03 | passed |
| P2-04 | passed |
| P2-05 | passed |
| P2-06 | passed as a local commit only |

## Acceptance dimensions after the 2026-09-24 local pass

| Dimension | Status |
|---|---|
| Source ingestion | passed (Phase 1); Q1–Q120 register unchanged |
| Local technical validation | passed |
| Governance consistency | re-checked after this edit; 71/58 IDs unchanged |
| Business acceptance | not granted; Faruk confirmation remains pending |
| Named stakeholder acceptance | pending Faruk, Ann, and specialists |
| Production readiness | not claimed |
| Legal, provider, and deployment approval | not claimed |
| Real-data migration readiness | not claimed |

Technical acceptance here means the local Phase 2 kernel passed the gates in
this file. It does not authorize production, a hosted database, a live
provider, a push, or Phase 3.

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

Isolated rows were inserted into local `perchpoint_phase2` and deleted afterward.
Leftover benchmark properties: 0. Elm Court remained. Dataset: 1,000 properties,
1,000 buildings, 2,000 spaces, 1,000 listings, 1,000 inquiries, 250,000 activity
rows spread across those properties (250 each). The scale load uses the seeded
demonstration organization. A second organization and an expired membership
already exist in the development seed and are covered by authorization tests.
Reads used `perchpoint_runtime` and transaction-local organization context.
Warmup: 1. Measured runs: 10. Each sample is one target statement plus one
`set_config` statement. No ORM N+1 loop was used.

| Query | p50 ms | p95 ms | max ms | Plan evidence |
|---|---:|---:|---:|---|
| Property list, 50 rows | 12.43 | 12.59 | 14.23 | Sequential scan, 1,000 rows, 11.854 ms |
| Property hierarchy | 22.40 | 22.75 | 24.62 | Sequential scans, one building and the space table, 21.868 ms |
| Inquiry queue, 50 rows | 11.78 | 11.93 | 12.14 | Sequential scan, 1,000 rows, 11.080 ms |
| Inquiry detail | 0.77 | 0.80 | 0.81 | Primary-key index scan, 0.093 ms |
| Activity timeline, 50 rows | 3.30 | 3.44 | 3.59 | Bitmap index scan on `activity_resource_time`, 250 rows, 2.546 ms |
| Public published listings | 0.90 | 1.01 | 1.16 | Function scan, 333 rows, 0.268 ms |
| Public listing detail | 0.87 | 0.89 | 0.91 | Function scan, 1 row, 0.248 ms |
| Concurrent public listings, 4 workers x 2 | 21.24 | 41.90 | 42.80 | Separate runtime connections |

These are under the 500 ms ordinary-read planning ceiling. A timeline that
sorted all 250,000 rows for one resource was about 2.5 s, so migration
`0006_activity_index` indexes `(organization_id, resource_id, occurred_at)`.
The hierarchy and list scans stay sequential because the planner prefers them
at this cardinality; no additional index was added. Hardware was the local
Windows PostgreSQL 16 process. The design mix of 3,000 spaces, 5,000 people,
25,000 inquiries, and 25 concurrent users was not executed.

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
| Browser journeys and accessibility | P2-04 / P2-05 | Playwright plus axe | passed: 14 tests, exit 0; axe critical and serious empty on `/` and the signed-in platform workspace |
| Measured performance | P2-05 | benchmark harness | passed for the measured reads below 500 ms; full design mix not executed |
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

## Acceptance dimensions after the 2026-09-24 local pass

| Dimension | Status |
|---|---|
| Source ingestion | passed (Phase 1); Q1–Q120 register unchanged |
| Local technical validation | passed for the gates recorded in this file |
| Governance consistency | re-checked after this edit; 71/58 IDs unchanged |
| Business acceptance | not granted; Faruk confirmation remains pending |
| Named stakeholder acceptance | pending Faruk, Ann, and specialists |
| Production readiness | not claimed |
| Legal, provider, and deployment approval | not claimed |
| Real-data migration readiness | not claimed |

Technical acceptance here means the local Phase 2 kernel passed the gates in
this file. It does not authorize production, a hosted database, a live
provider, a push, or Phase 3.

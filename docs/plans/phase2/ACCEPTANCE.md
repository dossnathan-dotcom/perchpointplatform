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

Isolated rows named `Bench *` were inserted into local `perchpoint_phase2`,
read through `perchpoint_runtime` with transaction-local organization context,
then deleted. Leftover benchmark rows: 0. Dataset: 1,000 properties. Query:
`SELECT id, name FROM properties WHERE name LIKE 'Bench %' ORDER BY id LIMIT 50`.
Warmup: 1. Measured runs: 20. p50 12.24 ms, p95 12.42 ms, max 12.43 ms.
This is below the planning read ceiling of 500 ms for this query only.
Buildings, spaces, inquiries, the 250,000-activity design, concurrency, and
`EXPLAIN ANALYZE` were not part of this run. The larger design remains unproven.
Browser, responsive, and accessibility gates were not executed in this pass.

## Required evidence (P2-01 through P2-05)

| Evidence | Package | Planned command / method | Status now |
|---|---|---|---|
| Contract generation and compatibility | P2-01 | `python -m foundation.export --check`; TS `--check` | planned |
| Clean and upgrade migrations | P2-02 | `alembic upgrade` / `downgrade` / `upgrade` | blocked: no PostgreSQL tooling |
| Organization-aware constraints | P2-02 | constraint pytest as runtime role | planned |
| Direct DB + API authorization | P2-02 | `test_rls.py` | planned |
| Actor and pooled-context isolation | P2-02 | two-checkout leak test | planned |
| Atomic domain/audit/outbox/idempotency | P2-03 | command runner tests | planned |
| Concurrent retries and stale edits | P2-03 | threaded/async pytest | planned |
| Worker crash recovery | P2-03 | kill-and-reclaim test | planned |
| Fake webhook authenticity, dedupe, order | P2-03 | `test_inbox.py` | planned |
| Redaction and scoped projections | P2-03 / P2-04 | log + public GET tests | planned |
| Historical relationship correctness | P2-01 / P2-02 | effective-dated fixtures | planned |
| Browser journeys and accessibility | P2-04 / P2-05 | listed journeys below | planned |
| Measured performance | P2-05 | benchmark harness | planned |
| Existing Phase 0/1 regression gates | P2-05 | established suite | historical 2026-09-23 evidence; not re-certified this turn |

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

## Acceptance dimensions after this planning turn

| Dimension | Status |
|---|---|
| Source ingestion | passed (Phase 1) |
| Technical validation of this plan | planning complete; implementation unstarted |
| Governance consistency | planning aligned; 71/58 IDs unchanged |
| Provisional business acceptance | Nathan-approved interview direction; Faruk confirmation still pending for reserved policy |
| Named stakeholder acceptance | pending Faruk, Ann, specialists |
| Production readiness | blocked |

# Phase 2 Implementation Plan

Classification: planning. Do not start P2-01 application code until Nathan
approves this package.

Owners: Nathan (technical), unless a row names Faruk or Ann for acceptance.

## Sequence

Cursor audit and contracts (this package, then P2-01) → Nathan plan approval →
reference core (P2-02, P2-03) → contract freeze → bounded Emergent UI (P2-04) →
Cursor review (P2-05) → verification and acceptance (P2-06).

## P2-00 — Repository audit and planning

Status: **this turn**.

- Reuse: entire Phase 0/1 corpus, `AGENTS.md`, Cursor rules, foundation
  contracts, existing tests.
- New: `docs/plans/phase2/**`, conflict/assumption/dependency updates.
- Not created: runtime packages, migrations, lockfile edits.
- Tests: source and governance validators only as diagnostics.
- Stop: material unresolved source conflict that existing decisions cannot
  resolve. None found that blocks planning.
- Rollback: delete or revise planning files; no schema to roll back.
- Owner: Nathan.

## P2-01 — Domain architecture and canonical contracts

Prerequisites: Nathan approval of this plan; P2-00. The numbered-questionnaire
blocker is cleared by `APPROVED_CUSTOMIZATION_ANSWERS.md` and
`ANSWER_TRACEABILITY.md` (Q1–Q120, references resolved). That record authorizes
this package only. It is not P2-02 authorization and it is not Phase 2 exit
evidence.

Status: **local P2-02/P2-03 reference persistence is implemented on this branch.**
The 2026-09-24 follow-up instruction authorized packages P2-02 through P2-06
and local commits. A later completion assignment the same day authorizes
finishing those packages. Q120's original approval history stays unchanged in
`APPROVED_CUSTOMIZATION_ANSWERS.md`. This does not record Faruk, Ann, counsel,
or accounting signoff, and it does not make production ready.

Historical P2-01 note: contract checks passed for that package before this
authorization. Database evidence belongs to the PostgreSQL tests, not to the
P2-01 model tests.

Reuse:

- `backend/foundation/base.py`, `property.py`, `people.py`, `governance.py`,
  `workflows.py`, `integrations.py`, `seeds.py`, `export.py`
- `contracts/generated/*`, `contracts/fixtures/*`
- `frontend/scripts/generate-contract-types.cjs`
- `docs/phase0/CANONICAL-MODEL.md` as historical contract notes

Proposed new/changed:

- Evolve selected models to `0.2.0`: ownership/management/portfolio
  relationships; space-state fields; inquiry/activity/task/approval read
  models; command/error envelopes.
- `docs/phase0/CANONICAL-MODEL.md` addendum pointing at CONFLICT-008/009
- New schemas generated via exporter only

Schema: additive. Preserve seed UUIDs. Do not regenerate `sid()` names.

Tests:

```text
cd backend
python -m foundation.export --check
python -m pytest -q tests/test_foundation_contracts.py
cd ../frontend
node scripts/generate-contract-types.cjs --check
```

Failure modes: silent hierarchy rewrite; broken generated types.
Mitigation: dual-read projections; fixture ID snapshot test.
Rollback: revert contract commit; regenerate.
Stop: any requirement to drop Phase 0 fixture IDs.
Owner: Nathan.

## P2-02 — Reference persistence and access security

Prerequisites: P2-01; local PostgreSQL 16 or local Supabase (D-011).

Reuse: permission vocabulary in `backend/foundation/permissions.py`;
`bcrypt` / `passlib` / `PyJWT` already in `backend/requirements.txt`.

Proposed new:

- `backend/perchpoint/db/*`
- `backend/perchpoint/auth/*`
- `backend/alembic.ini`, `backend/alembic/env.py`,
  `backend/alembic/versions/0001_phase2_reference.py`
- Candidate libraries (versions to pin only at install time, after approval):
  SQLAlchemy `2.0.x`, Alembic `1.13+` or `1.16.x`, psycopg `[binary] 3.2.x`
- `backend/tests/phase2/test_rls.py`, `test_constraints.py`,
  `test_local_auth.py`

Do not install those libraries in the planning turn.

Schema consequences: organizations, entities, relationships, properties,
buildings, spaces, people, household membership, local identities,
memberships, listings, inquiries, activity, audit, outbox, inbox,
idempotency keys. Composite unique `(organization_id, id)` and FK pairs.

Tests must run as `perchpoint_runtime`. Memory or SQLite is not evidence.

```text
alembic upgrade head
alembic downgrade base && alembic upgrade head
pytest backend/tests/phase2/test_rls.py backend/tests/phase2/test_constraints.py
```

Failure modes: owner-connected false pass; context leak; missing org on FK.
Mitigation: role-enforced test fixtures.
Rollback: `alembic downgrade`; drop local DB.
Stop: no local PostgreSQL; do not skip and claim pass.
Owner: Nathan.

## P2-03 — Commands, audit, inbox/outbox, worker

Prerequisites: P2-02.

Reuse: `AuditEvent`, `DomainEvent`, `OutboxRecord`, `InboxRecord`,
`AdapterCommand` contracts.

Proposed new:

- `backend/perchpoint/commands/submit_inquiry.py`
- `backend/perchpoint/commands/triage_inquiry.py`
- `backend/perchpoint/commands/runner.py`
- `backend/perchpoint/events/*`
- `backend/perchpoint/adapters/fake_provider.py`
- `backend/perchpoint/adapters/message_sink.py`
- `backend/perchpoint/workers/outbox_worker.py`
- `backend/tests/phase2/test_commands.py`
- `backend/tests/phase2/test_worker.py`
- `backend/tests/phase2/test_inbox.py`

Tests: identical/concurrent retries; fingerprint mismatch; in-progress;
stale version; crash before response; two-worker claim; lease expiry;
dead letter; signed webhook; out-of-order; redaction.

Rollback: disable worker flag; retain rows; compensating reverse command
later. Forward recovery preferred over silent delete.
Stop: any live provider URL or credential.
Owner: Nathan.

## P2-04 — Frozen-contract connected UI

Prerequisites: P2-03 plus a **contract-freeze commit** Nathan identifies as
the Emergent base.

Reuse:

- `frontend/src/App.js` routing and Phase 0 navigation fixes
- `frontend/src/components/*` design system, listings, portal shells
- `frontend/src/App.css`, `design_guidelines.json`
- Yarn 1.22.22 frozen install

Proposed change (Cursor or Emergent inside envelope):

- New persistent views only under approved paths in
  `EMERGENT_HANDOFF.md`
- Generated client consumption; no parallel fetch types
- Loading, empty, invalid, denied, missing, stale-version, transient
  failure, retry, and success-persistence states on every changed journey
- No success toast for unimplemented actions

Forbidden in this package: Next.js rewrite; design-system replacement;
canonical schema edits; auth/RLS/migration edits.

Tests:

```text
cd frontend
corepack yarn install --frozen-lockfile --non-interactive
corepack yarn test --watchAll=false --runInBand
# plus browser journeys listed in ACCEPTANCE.md
```

Rollback: revert UI commit; contracts remain.
Stop: Emergent edits `backend/foundation`, Alembic, or RLS.
Owner: Nathan (review); Emergent (visual slice only after freeze).

## P2-05 — Verification and hardening

Prerequisites: P2-04 return diff.

Reuse: existing Phase 0/1 gates.

Add: property-based tests (Hypothesis, if approved) for idempotency and
transition guards; selective mutation testing on command runner and RLS
policies only.

Must re-run: governance, source integrity, backend, frontend, lint, typing,
export `--check`, generated TypeScript `--check`, compileall, Ruff, Mypy.

Stop: any skipped required Phase 2 test marked passed; any `/app` reintroduction.
Owner: Nathan.

## P2-06 — Acceptance and handoff

Prerequisites: P2-05 green.

Deliver: Phase 2 acceptance report, measured benchmark notes, Emergent
return review, and explicit later-phase backlog. No production promotion.

Owner: Nathan technical acceptance. Faruk/Ann/specialists remain pending
for their domains. Production remains blocked.

## Later-phase reuse (not this plan)

Production identity and MFA; CI and hosted infrastructure; generalized
documents; actual payments/screening/leasing; maintenance operations and
mobile app; Innago migration execution; launch. Reuse this kernel.

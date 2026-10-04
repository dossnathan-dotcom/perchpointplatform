# Phase 6 scope and gates

## Purpose

Phase 6 establishes local, production-shaped identity and access controls without activating a
hosted identity tenant or real users. It implements the approved Q1–Q160 decisions only within
the existing modular monolith, PostgreSQL boundary, and Phase 5 records.

## In scope

- Local Supabase Auth/GoTrue authentication behind a replaceable provider adapter.
- Stable PerchPoint identity accounts separate from provider subjects, parties, households,
  memberships, employment, vendor relationships, occupancies, and assignments.
- Password policy, TOTP MFA, recovery codes, supervised privileged recovery, contact changes,
  server-custodied sessions, CSRF/origin checks, session rotation and revocation.
- Hybrid capability and attribute authorization, effective-dated memberships, scopes, forced
  RLS, relationship isolation, authorized directories, search/storage/export/cache/worker
  boundaries, and a deliberate public listing projection.
- Relationship-bound invitations and onboarding; role/scope requests and decisions; access
  reviews; suspension, restoration, and offboarding history.
- Bounded, non-transitive delegation; purchasing authority; split-transaction detection;
  owner-reserved decisions; vendor-worker approval; service principals and one-time credentials.
- Connected identity/access UI and local tests, benchmark tooling, clean-room procedure,
  runbook, traceability, and acceptance gates.

## Explicitly out of scope

- Hosted Supabase configuration or proof, production secrets, paid providers, real email, real
  users, production data, deployment, or launch.
- Social login or custom WebAuthn/passkey implementation.
- Autonomous housing, legal, spending, payment, ledger, capital-project, employment, or
  dangerous-maintenance decisions.
- Shared credentials, implicit super-roles, provider-defined business roles, direct bucket
  authorization, or client-side authorization.
- Production retention policy, legal approval, or Phase 7 capability activation.

## Authority and acceptance

- Nathan owns technical implementation and local technical acceptance.
- Faruk owns material business authority, owner-reserved decisions, material delegation policy,
  and production launch.
- Ann owns operational fit for workforce, vendor, leasing, maintenance, and access workflows.
- Accounting, maintenance, and qualified legal specialists accept only their domains.
- No authority may substitute for another. Q1–Q160 approval does not equal implementation
  evidence, hosted acceptance, stakeholder acceptance, or production authorization.

## Dependencies

Phase 6 depends on the Phase 2 modular monolith and forced-RLS architecture, Phase 3 environment
and secret boundaries, Phase 4 connected UI/accessibility conventions, Phase 5 canonical
records/search/storage/export controls, PostgreSQL, local GoTrue, Mailpit, and the pinned
container/toolchain definitions. GitHub remains canonical; acceptance cannot depend on
uncommitted state.

## Primary risks and controls

- **Authority drift:** current membership, role bundle, scope, relationship, AAL, delegation,
  and policy state are checked at action time; stale token metadata is not authority.
- **Cross-tenant or existence leakage:** forced RLS and authorized query boundaries cover rows,
  counts, snippets, suggestions, exports, storage access, and directories.
- **Credential compromise:** provider password/TOTP custody, opaque HttpOnly cookies, encrypted
  refresh custody, CSRF/origin checks, rotation/reuse response, revocation, and redacted logs.
- **Self-approval or threshold evasion:** explicit self-grant/self-approval denial,
  non-transitive delegation, amount/resource/decision bounds, and related-transaction
  aggregation.
- **False completion:** all unexecuted tests remain placeholders; external gates are
  `BLOCKED_EXTERNAL`.

## Gate state

The authoritative human-readable status is `EXECUTION_LEDGER.md`. At documentation closeout:

- Local gates P6-R0–P6-R14: `IN_PROGRESS` unless current-commit evidence changes the ledger.
- Independent review and Git/PR/CI/merge gates P6-R15–P6-R16: `NOT_STARTED`.
- Hosted Supabase: `BLOCKED_EXTERNAL`.
- Stakeholder/business acceptance: `BLOCKED_EXTERNAL`.
- Production readiness and launch: `BLOCKED_EXTERNAL`.

Requirements: `PP-GOV-002`, `PP-GOV-003`, `PP-AUTH-001`, `PP-AUTH-002`,
`PP-AUTH-003`, `PP-AUTH-011`, `PP-SEC-002`, `PP-SEC-004`, `PP-NFR-002`,
`PP-ACCEPT-001`, `PP-ACCEPT-002`, `PP-ACCEPT-003`.

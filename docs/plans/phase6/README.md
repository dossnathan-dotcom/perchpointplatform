# Phase 6 — identity, authorization, and access governance

Status: documentation closeout in progress. Local technical acceptance is **not granted**.
Hosted Supabase, stakeholder acceptance, and production are `BLOCKED_EXTERNAL`.

Phase 6 adds provider-backed authentication, server-custodied sessions, effective-dated
identity and relationship records, deny-by-default authorization, forced RLS, bounded
delegation, workforce/vendor controls, and connected identity surfaces on top of Phase 5.
Supabase Auth is the intended hosted provider; local development uses pinned GoTrue. PerchPoint
retains business authority and never treats provider metadata, a URL, or a preview role as
authorization.

## Document map

- [SCOPE_AND_GATES.md](SCOPE_AND_GATES.md) — scope, exclusions, authority, dependencies, risks,
  and phase gates.
- [ARCHITECTURE.md](ARCHITECTURE.md) — component boundaries, identity/data separation, provider
  adapter, session lifecycle, and migration map.
- [AUTHORIZATION_AND_DATA.md](AUTHORIZATION_AND_DATA.md) — actor/capability matrix, scopes, RLS,
  relationship isolation, search, storage, export, cache, and public projection.
- [IDENTITY_LIFECYCLE.md](IDENTITY_LIFECYCLE.md) — invitations, onboarding, MFA, recovery,
  sessions, contacts, access reviews, suspension, and offboarding.
- [DELEGATION_WORKFORCE.md](DELEGATION_WORKFORCE.md) — delegation, approvals, purchasing,
  vendor/workforce boundaries, and service principals.
- [SECURITY_AND_UI.md](SECURITY_AND_UI.md) — threat model, security events, privacy, UI states,
  accessibility, and responsive behavior.
- [VERIFICATION_AND_RUNBOOK.md](VERIFICATION_AND_RUNBOOK.md) — test matrix, performance,
  clean-room, recovery, operations, and acceptance procedure.
- [ANSWER_TRACEABILITY.md](ANSWER_TRACEABILITY.md) — substantive Q1–Q160 implementation and
  evidence map.
- [EXECUTION_LEDGER.md](EXECUTION_LEDGER.md) — gate ownership and current status.
- [CHANGED_FILES.md](CHANGED_FILES.md) — implementation and documentation inventory.
- [adr/README.md](adr/README.md) — Phase 6 architecture decisions.

## Controlling sources

Precedence is defined by `docs/product/SOURCE_PRECEDENCE.md`. The 160 approved decisions in
`APPROVED_CUSTOMIZATION_ANSWERS.md` are the Phase 6 customization source; they remain bounded by
the Product Constitution and stable requirements in
`docs/governance/REQUIREMENTS_TRACEABILITY.md`. Conflicts are recorded in
`docs/source/provenance/SOURCE_CONFLICT_REGISTER.md`, never silently resolved.

## Implementation status

Implemented code includes local GoTrue integration, opaque HttpOnly sessions, TOTP, recovery
codes, invitation activation, effective membership checks, capability bundles, forced RLS,
delegations and usage records, purchasing boundaries, vendor-worker approval, access reviews,
identity lifecycle events, service credentials, security events, and connected Phase 6 UI
surfaces. This is a description of repository state, not an acceptance claim.

The development JWT is excluded from supported interactive startup. Tests may set
`PHASE6_ALLOW_DEV_JWT=1` only for isolated legacy fixtures. All Phase 6 users and messages remain
synthetic. No real users, production data, provider activation, or Phase 7 work are authorized.

Requirements: `PP-PROD-001`, `PP-GOV-001`, `PP-GOV-002`, `PP-AUTH-001`,
`PP-AUTH-011`, `PP-SEC-001`, `PP-NFR-002`, `PP-ACCEPT-001`, `PP-ACCEPT-003`.

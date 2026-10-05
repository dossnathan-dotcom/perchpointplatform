# ADR-P6-001 — Provider authentication, PerchPoint authority

Status: accepted for Phase 6 local design; hosted/production activation blocked.

## Context

Q1–Q10 select Supabase Auth while requiring stable PerchPoint identity, environment separation,
and PerchPoint-owned business authorization.

## Decision

Use pinned local GoTrue for password, recovery, and TOTP verification behind
`phase6_provider.py`. Verify only required token integrity/identity/assurance claims and map the
immutable provider subject to a PerchPoint identity. Store no business role or approval authority
in provider metadata. Keep the provider schema/database outside Alembic.

## Consequences

The provider is replaceable and compromise of role metadata cannot grant business authority.
PerchPoint must maintain identity mapping, current membership/policy checks, fail-closed provider
errors, and reconciliation. Hosted configuration and operational proof are separate gates.

Source: Q1–Q10. Owner/acceptance: Nathan. Requirements: `PP-AUTH-001`, `PP-PROP-002`,
`PP-PROV-002`, `PP-AUTH-011`, `PP-SEC-001`.

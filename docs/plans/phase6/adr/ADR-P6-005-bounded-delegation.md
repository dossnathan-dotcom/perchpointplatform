# ADR-P6-005 — Bounded delegation and usage history

Status: accepted for Phase 6 local design; business/production acceptance blocked.

## Context

Q111–Q127 require attributable, scoped, expiring, non-transitive delegation while preserving
owner reservations, purchasing limits, separation of duties, and immutable evidence.

## Decision

Store each grant with grantor/grantee, organization, capability, resource, decision types,
amount ceiling, dates, reason, approval, policy version, status, and events. Limit default
duration to 30 days, prohibit self-delegation and owner-reserved capabilities, reauthorize every
use, aggregate related transactions, and append immutable usage records. Keep technical
administration separate from business approval.

## Consequences

Delegated work is reconstructable and revocable without shared approval codes. Commands must
carry enough context to evaluate and record usage. Policy changes need prospective versions and
Faruk approval when business authority changes.

Source: Q111–Q127. Owners/acceptance: Faruk for business authority; Nathan for implementation;
Ann for operational workflow. Requirements: `PP-AUTH-002`, `PP-AUTH-003`,
`PP-FIN-002`, `PP-FIN-006`, `PP-MAINT-002`, `PP-SEC-004`.

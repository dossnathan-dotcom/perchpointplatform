# ADR-P6-004 — Separate identity and business relationships

Status: accepted for Phase 6 local design.

## Context

Q4–Q5 and Q11–Q20 require identity continuity while distinguishing account, party, household,
occupancy, membership, employment, vendor, assignment, and non-human actors.

## Decision

Map immutable provider subject to a stable PerchPoint identity. Keep contact fields mutable and
non-authoritative. Represent each business relationship separately and effective-date it.
Derive resident/vendor/worker access from current relationships, never typed addresses. Keep
one account per adult/worker and model machine actors as non-interactive service principals.

## Consequences

Applicant-to-resident continuity does not merge unrelated records. Shared credentials and fake
employees are unnecessary. Authorization must join current relationships and preserve historical
state; onboarding/offboarding cannot be implemented as destructive account deletion.

Source: Q4–Q5, Q11–Q20, Q34–Q39, Q128–Q130, Q141–Q150. Owners: Nathan (technical), Ann
(operational), Faruk (business). Requirements: `PP-AUTH-010`, `PP-DATA-004`,
`PP-DATA-005`, `PP-WORK-001`, `PP-WORK-002`, `PP-PROP-002`.

# ADR-P6-003 — Typed hybrid authorization plus forced RLS

Status: accepted for Phase 6 local design; complete adversarial evidence pending.

## Context

Q21–Q40 and Q91–Q110 require granular capabilities, contextual scopes, current relationships,
separation of duties, route/command/query/channel enforcement, and forced RLS.

## Decision

Keep a typed policy module inside the modular monolith. Treat role bundles as candidate
capabilities and require applicable organization, resource, relationship, state, AAL,
delegation, amount, and decision attributes. Deny by default. Enforce at the application
boundary and through forced PostgreSQL RLS using transaction-local context. Apply the same
authority to search, storage, exports, caches, workers, and public projections.

## Consequences

Authorization remains inspectable and avoids a premature external policy engine. Policy and
database controls can drift unless migration, direct API, and direct RLS tests cover both.
Frontend visibility is never a security boundary.

Source: Q21–Q40, Q91–Q110, Q156–Q157. Owner/acceptance: Nathan; Faruk for business authority;
Ann for operational fit. Requirements: `PP-AUTH-001`, `PP-AUTH-002`, `PP-AUTH-008`,
`PP-DATA-006`, `PP-DATA-007`, `PP-WORK-001`.

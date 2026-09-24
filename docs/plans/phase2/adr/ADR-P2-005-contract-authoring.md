# ADR-P2-005 Single contract authoring authority

Status: proposed (pending Nathan approval)

## Context

Phase 0 already forbids hand-editing `contracts/generated`,
`contracts/fixtures`, `frontend/src/data/generated`, and
`frontend/src/contracts/generated.d.ts`. Parallel OpenAPI or TypeScript
types would drift.

## Decision

Keep `backend/foundation/` as the authoring authority for Phase 2 contract
changes. OpenAPI is generated from the same models. Compatibility is
versioned (`0.1.0` → additive `0.2.0`). Missing endpoints require a contract
change request, not a parallel implementation.

## Consequences

- Export and TypeScript `--check` remain release gates.
- Emergent is forbidden from editing authoring models.

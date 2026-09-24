# ADR-P2-004 Preserve the React application

Status: proposed (pending Nathan approval)

## Context

The public site and eight role-preview shells already exist in React 19 /
CRA / CRACO with approved navigation fixes and a frozen Yarn 1.22.22 graph.
An automatic Next.js rewrite would discard working UX without evidence.

## Decision

Incrementally refactor the existing React application. Do not replace the
design system or rebuild working navigation without a recorded defect.
Emergent may add a connected visual slice only after contract freeze.

## Consequences

- Yarn lockfile remains canonical.
- New persistent views must reuse current visual language.
- Frontend cannot become a second backend.

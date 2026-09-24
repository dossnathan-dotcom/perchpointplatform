# PerchPoint Repository Instructions

PerchPoint is the HawkVision Homes property operating system. Start with
`docs/product/PRODUCT_CONSTITUTION.md`, `docs/product/SOURCE_PRECEDENCE.md`, and
`docs/governance/REQUIREMENTS_TRACEABILITY.md`.

## Non-negotiable workflow
- Preserve unrelated work. Never use destructive Git commands.
- GitHub is canonical; no release may depend on uncommitted agent state.
- Do not edit generated files under `contracts/generated`, `contracts/fixtures`,
  `frontend/src/data/generated`, or `frontend/src/contracts/generated.d.ts`.
- Regenerate through `python -m foundation.export` and
  `node scripts/generate-contract-types.cjs`.
- Use Yarn 1.22.22 as the only frontend package manager. Reproduce dependencies from
  `frontend/` with `corepack yarn install --frozen-lockfile --non-interactive`; do not add
  npm, pnpm, or Bun lockfiles.
- Treat role previews as synthetic UX, never authentication or authorization.
- Deny sensitive access by default; enforce sensitive actions on the server in later phases.
- Keep provider state, operational records, and formal accounting facts distinct.
- Record evidence, exact commands, failures, skips, and limitations.
- Stop at the approved phase boundary. Phase 1 does not authorize production integrations.

## Acceptance
Nathan owns technical/product acceptance; Faruk owns material business acceptance; Ann owns
operational acceptance; accounting, maintenance, and legal specialists accept only their
domains. Never substitute one authority for another.

Requirements: `PP-GOV-002`, `PP-GOV-005`, `PP-SEC-001`, `PP-ACCEPT-001`,
`PP-ACCEPT-002`, `PP-NFR-002`.

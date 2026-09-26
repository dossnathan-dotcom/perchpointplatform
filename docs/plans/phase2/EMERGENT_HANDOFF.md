# Phase 2 Emergent Handoff

Status: **not ready**. Local planning does not authorize Emergent UI work.

Nathan approved: Cursor audit and contracts → Nathan plan approval → reference
core → contract freeze → bounded Emergent UI → Cursor review → verification.

## Current checkpoint (2026-09-24 inspection)

| Item | Value |
|---|---|
| Branch | `cursor/phase-01-governance-audit` |
| Local HEAD | `494c5fb8030a003b563e11c495c749ef467d42cb` |
| Emergent / Phase 1 baseline ancestor | `9706914916c124784bd1bad3715de239e2774469` |
| `origin/cursor/phase-01-governance-audit` | same SHA as local HEAD (`git ls-remote` succeeded) |
| Working tree at inspection | clean of Phase 2 implementation; planning files uncommitted |
| Frozen implementation commit | **none yet** |

An earlier 403 while pushing as `natedoss` is historical. The branch is now
reachable on origin at the closure commit. That restores remote backup of
Phase 1. It does **not** create a frozen Phase 2 contract base and does **not**
authorize Emergent to start.

## Required before Emergent starts

1. Nathan approves this planning package.
2. Cursor completes P2-01 through P2-03 on a dedicated Phase 2 branch.
3. Nathan identifies a **contract-freeze commit**.
4. Handoff fields below are filled with that commit, not `494c5fb`.

## Handoff envelope (to complete at freeze)

- Verified accessible base commit and branch: _pending freeze_
- Frozen API / schema / error / event contracts: `contracts/generated/`,
  `backend/foundation/`, OpenAPI from FastAPI
- Generated client location: `frontend/src/contracts/generated.d.ts` and the
  existing generator; any new client wrapper lives under
  `frontend/src/api/` and is generated or thin
- Allowed frontend paths:
  - `frontend/src/components/` for listing/triage/activity views
  - `frontend/src/App.js` route additions only for approved persistent views
  - `frontend/src/App.css` only if required for those views
- Forbidden core changes:
  - `backend/foundation/`
  - `backend/alembic/`
  - `backend/perchpoint/auth/`, `db/`, `commands/`, `events/`, `workers/`
  - `backend/requirements.txt`, `frontend/yarn.lock`, package-manager changes
  - RLS policies, audit/event semantics, financial logic, production config
- Synthetic setup: local backend + published listing fixtures; preview flags
  remain separate from authenticated `/api/v2` sessions
- Route inventory: keep `/`, `/rentals/:unitId`, `/perchpoint/:roleId/:viewId?`,
  `/foundation/:sectionId?`; add only documented persistent staff/public
  listing routes
- Design assets: existing premium public and dense internal styles
- Acceptance cases: `ACCEPTANCE.md` journey matrix
- Return-diff expectations: frontend-only plus documented client wrappers;
  no schema drift

If an endpoint is missing, Emergent files a contract change request. It must
not invent a parallel backend.

## Message sink and identities

Emergent may use documented synthetic local users. It must not invite or
contact Faruk, Ann, residents, or vendors.

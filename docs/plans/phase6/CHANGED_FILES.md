# Phase 6 changed-file inventory

This inventory describes the observed Phase 6 implementation and documentation surface. It is
not acceptance evidence and does not assert that every untracked file is complete or merged.
Generated artifacts, evidence, backend, frontend, scripts, and workflows are read-only inputs
to this documentation-only change.

## Documentation

- `docs/plans/phase6/APPROVED_CUSTOMIZATION_ANSWERS.md` — Q1–Q160 approved decisions.
- `docs/plans/phase6/README.md` — package index and status.
- `docs/plans/phase6/SCOPE_AND_GATES.md` — scope, exclusions, authority, risks, gates.
- `docs/plans/phase6/ARCHITECTURE.md` — architecture and migration map.
- `docs/plans/phase6/AUTHORIZATION_AND_DATA.md` — matrix, policy, RLS and channel isolation.
- `docs/plans/phase6/IDENTITY_LIFECYCLE.md` — invitation/auth/MFA/recovery/session/lifecycle.
- `docs/plans/phase6/DELEGATION_WORKFORCE.md` — approvals, spending, vendors and machines.
- `docs/plans/phase6/SECURITY_AND_UI.md` — threat model, events, UI and accessibility.
- `docs/plans/phase6/VERIFICATION_AND_RUNBOOK.md` — test/benchmark/clean-room/runbook.
- `docs/plans/phase6/ANSWER_TRACEABILITY.md` — Q1–Q160 traceability.
- `docs/plans/phase6/EXECUTION_LEDGER.md` and `ACCEPTANCE.md` — gate state.
- `docs/plans/phase6/adr/` — architecture decisions.
- `docs/governance/README.md`, `docs/README.md` — indexes.
- `docs/source/provenance/SOURCE_CONFLICT_REGISTER.md` — controlling source conflicts.

## Application modules

- `backend/perchpoint/phase6_provider.py` — local GoTrue adapter and claim verification.
- `backend/perchpoint/phase6_identity.py` — session, invitation, MFA/recovery, delegation,
  access-request, service credential, and privileged-recovery services.
- `backend/perchpoint/phase6_policy.py` — password, role/capability, authority, and recovery rules.
- `backend/perchpoint/phase6_provision.py` — synthetic provider/identity provisioning.
- `backend/perchpoint/routes.py` — Phase 6 HTTP routes and enforcement.
- `backend/perchpoint/bootstrap.py`, `db.py`, `seed.py`, `settings.py` — environment,
  transaction context, seed, and fail-closed startup support.
- `frontend/src/components/portal/Phase6SignIn.jsx` — unified sign-in.
- `frontend/src/components/portal/Phase6Access.jsx` — identity/access surfaces and states.
- `frontend/src/components/portal/Phase6Access.test.js` — connected UI component checks.

## Database migrations

- Alembic versions and paired SQL `0012_phase6_identity` through
  `0030_phase6_recovery_provider`, excluding number `0029` SQL because its reauthorization
  change is contained in the version implementation.
- See `ARCHITECTURE.md#migration-map` for responsibilities.

## Tests and tools

- `backend/tests/phase6/test_identity.py` — Phase 6 backend/database integration tests.
- `backend/tests/phase2/test_commands_and_authorization.py` — direct command/authorization
  regression coverage used by Phase 6.
- `scripts/validate_phase6_answers.py` — exact Q1–Q160 identifier validation.
- `scripts/phase6_auth_up.py`, `phase6_auth_restart.py` — local provider lifecycle.
- `scripts/phase6_browser_evidence.py` — browser evidence runner.
- `scripts/phase6_scale.py`, `phase6_benchmark.py` — synthetic workload and benchmark.
- `scripts/phase6_acceptance.py` — fail-closed acceptance-state orchestration.
- `docker-compose.phase6.yml`, `docker-compose.phase6-closeout.yml` — local stacks.
- `.github/workflows/ci.yml` — observed CI integration.
- `test_reports/phase6/acceptance-state.json` — machine gate state; not modified here.

## Scope safeguard

No file outside `docs/` is authorized for modification by this documentation closeout. Build
outputs, caches, generated contracts, fixtures, and evidence remain untouched.

Requirements: `PP-GOV-002`, `PP-GOV-005`, `PP-ACCEPT-001`, `PP-NFR-002`.

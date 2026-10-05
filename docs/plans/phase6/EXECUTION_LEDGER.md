# Phase 6 execution ledger

This ledger is the human-readable companion to
`test_reports/phase6/acceptance-state.json`. The JSON record is authoritative for the
fail-closed checker. A gate is `PASSED` only when its current-commit evidence was generated
by the recorded command. Hosted, stakeholder, and production gates remain separate from
local technical acceptance.

| Gate | Requirement | Classification | Owner | Acceptance authority | Status |
| --- | --- | --- | --- | --- | --- |
| P6-R0 | Preflight and gap analysis | local | Nathan | Nathan | IN_PROGRESS |
| P6-R1 | Auth provider architecture | local | Nathan | Nathan | IN_PROGRESS |
| P6-R2 | Session and browser security | local | Nathan | Nathan | IN_PROGRESS |
| P6-R3 | Identity and account lifecycle | local | Nathan | Nathan | IN_PROGRESS |
| P6-R4 | Central authorization and forced RLS | local | Nathan | Nathan | IN_PROGRESS |
| P6-R5 | Search, storage, exports, cache, workers, and outbox | local | Nathan | Nathan | IN_PROGRESS |
| P6-R6 | Delegation, approvals, and purchasing | local | Faruk / Nathan | Faruk / Nathan | IN_PROGRESS |
| P6-R7 | Users, vendors, reviews, and service principals | local | Ann / Nathan | Ann / Nathan | IN_PROGRESS |
| P6-R8 | Connected frontend | local | Nathan | Nathan / Ann | IN_PROGRESS |
| P6-R9 | Threat model and adversarial tests | local | Nathan | Nathan | IN_PROGRESS |
| P6-R10 | Complete automated suites | local | Nathan | Nathan | IN_PROGRESS |
| P6-R11 | Three-browser, accessibility, keyboard, and responsive proof | local | Nathan | Nathan | IN_PROGRESS |
| P6-R12 | Clean-room and recovery proof | local | Nathan | Nathan | IN_PROGRESS |
| P6-R13 | Three-round authorization benchmark | local | Nathan | Nathan | IN_PROGRESS |
| P6-R14 | Documentation and governance closeout | local | Nathan | Nathan | IN_PROGRESS |
| P6-R15 | Independent review and remediation | local | Nathan | Nathan | NOT_STARTED |
| P6-R16 | Git, PR, CI, merge, and main verification | local | Nathan | Nathan | NOT_STARTED |
| P6-HOSTED | Hosted Supabase acceptance | hosted | Nathan | Nathan | BLOCKED_EXTERNAL |
| P6-STAKEHOLDER | Stakeholder and business acceptance | stakeholder | Faruk / Ann | Faruk / Ann | BLOCKED_EXTERNAL |
| P6-PRODUCTION | Production readiness and launch | production | Faruk / Nathan | Faruk / Nathan | BLOCKED_EXTERNAL |

## Historical incidents

- GoTrue startup first failed because the provider began before its `auth` schema existed.
- A retry then ran while the provider container was restarting.
- Both attempts remain failed historical attempts. The later separate `perchpoint_auth`
  initialization remediated them; current reproducibility must still be proved by P6-R12.
- The stale Phase 5 webpack-cache process was not controlled Phase 6 evidence and is excluded.
- Migration `0015_phase6_governance` first failed because forced RLS correctly prevented the
  migrator from seeding `capabilities`; the migration was corrected to use the narrowly
  granted non-login definer role.
- Migration `0017_phase6_rel_isolation` first failed because the original revision identifier
  exceeded Alembic's 32-character version column; the identifier was shortened and the
  migration then applied.

## External blockers

- **Hosted:** no hosted Supabase project credentials or hosted-provider authority. Owner:
  Nathan. Smallest external action: provide a HawkVision-owned nonproduction Supabase project
  and scoped credentials for the hosted acceptance run.
- **Stakeholder:** Faruk and Ann have not performed their business and operational acceptance.
  Smallest external action: review the green merged Phase 6 evidence and record their decisions.
- **Production:** production secrets, provider activation, legal/specialist gates, real-user
  onboarding, and deployment authority are unavailable. Smallest external action: complete the
  separately governed production-readiness review after hosted and stakeholder acceptance.

Requirements: `PP-AUTH-001`, `PP-AUTH-002`, `PP-SEC-001`, `PP-NFR-001`,
`PP-NFR-002`, `PP-ACCEPT-001`, `PP-ACCEPT-002`, `PP-ACCEPT-003`.

## Documentation closeout note

The Phase 6 package now includes scope/gates, architecture, identity lifecycle,
authorization/data isolation, delegation/workforce/service principals, threat model and
security events, UI/accessibility, verification/benchmark/clean-room/runbook, ADRs, changed-file
inventory, and substantive Q1–Q160 traceability. P6-R14 remains `IN_PROGRESS` until the
repository validator and documentation/link review run on the current commit and their evidence
is recorded outside this documentation-only change.

Behavioral clean-room, browser, RLS, and benchmark evidence remains bound to
`e4491b4396e323d3e5fd79c112a603f37fc32782`. A later image-package upgrade for the
fixed `libpcre2-8-0` finding does not replace that proof. The built API and web images
then scanned clean. Digest-pinned publisher images still report fixed findings in
publisher binaries; those scans are retained and do not replace the behavioral proof.
Requirements: `PP-SEC-001`, `PP-NFR-002`, `PP-ACCEPT-001`.

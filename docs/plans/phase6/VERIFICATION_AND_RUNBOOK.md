# Phase 6 verification and runbook

## Evidence rule

An implemented path or existing test name is not proof that it passed. A gate becomes `PASSED`
only when current-commit evidence records command, versions, start/end, exit code, skips,
warnings, environment, observations, failures/remediation, and artifact hashes. This document
defines required verification; it does not claim execution.

`test_reports/phase6/acceptance-state.json` is the fail-closed machine record and
`EXECUTION_LEDGER.md` is its human-readable companion. Evidence files are outside the
documentation-only scope of this change and have not been edited.

## Test matrix

| Area | Positive proof | Negative/adversarial proof | Principal implementation/tests |
| --- | --- | --- | --- |
| Provider/sign-in | Verified subject opens opaque session | bad signature/issuer/audience/method, generic failure, unavailable provider, dev JWT disabled | `phase6_provider.py`; `test_interactive_sign_in_*`, `test_development_jwt_*` |
| Invitation/onboarding | authorized invite, atomic activation, required MFA | expired/replayed/wrong email, resend invalidation, unauthorized/privileged role, delivery/provider failure rollback | migrations 0016/0020/0029; invitation tests |
| MFA/recovery/contact | TOTP confirm, codes, reset, supervised recovery, email continuity | unverified factor, replayed code/reset, self-recovery, missing approver/cooldown, refresh reuse | MFA/reset/recovery/email tests |
| Sessions | cookie/CSRF/origin, limits, list/revoke, key rotation | forged/missing CSRF, stale/expired membership, suspension, reuse, excess concurrency | session/CSRF/suspension/rotation tests |
| Authorization | valid capability/scope/AAL | guessed ID, forged headers, stale roles, self-grant/approval, wrong role/scope/AAL | policy tests; direct API suite |
| RLS/relationships | current org/household/assignment rows visible | no context, cross-org, other household/vendor/property, ordinary-admin bypass | forced-RLS and relationship tests |
| Delegation/spend | bounded grant/use and correct authority | transitive/expired/revoked/wrong capability/resource/decision/amount, split transactions, capital threshold | delegation and financial tests |
| Workforce/vendor | approved worker activation and assignment | shared/unauthorized proposal, unassigned data, expired assignment, self-approval | vendor-worker and relationship tests |
| Storage/search/export/cache | authorized row/field results and retrieval | counts/snippets/suggestions/object/export/cache leakage after revocation | Phase 5 suites plus Phase 6 channel tests |
| Service principal/worker | one-time scoped credential and lineage | interactive use, secret redisplay, expired/rotated key, replay, excessive capability | service credential test plus worker tests |
| Security events/logs | attributable required events | missing denial/high-risk event; secret/PII log scan | event API/database checks |
| UI/accessibility | complete connected workflows and states | denied/unavailable/provider failure/session expiry; keyboard/AT/responsive/reduced-motion | component tests plus Playwright/browser evidence |
| Lifecycle/reviews | review, revoke, suspend, restore deliberately | session survives, delegation/assignment resurrects, history mutates | access-review and lifecycle tests |

## Performance acceptance

Use the repository Phase 6 benchmark tooling against the defined 1,000-property synthetic
workload. Run three rounds after warm-up and retain raw measurements for authentication,
session resolution, representative authorized/denied route decisions, RLS list/detail queries,
revocation propagation, search, and export initiation. Record dataset hash, machine/container
resources, database state, percentiles, throughput/error rate, and regressions against the
approved budget. Do not report the benchmark passed from a single sample or an unrecorded run.

## Clean-room procedure

1. Start from a clean clone/worktree of the candidate commit; confirm no acceptance dependency
   on untracked files.
2. Record OS, Docker, Python, Node, Yarn 1.22.22, browser, database, and GoTrue versions.
3. Reproduce dependencies with documented lockfiles; do not introduce another package manager.
4. Create only synthetic local secrets/data. Confirm no production/hosted credentials.
5. Build/start the pinned Phase 6 stack, initialize the separate auth database, and migrate from
   zero to head.
6. Provision synthetic identities through supported tooling; run validation, backend,
   frontend, direct RLS, browser/accessibility, adversarial, benchmark, and recovery suites.
7. Restart services and verify session/provider failure recovery, then perform migration
   downgrade/restore procedure where supported.
8. Record every command/exit code, skip, warning, failure/remediation, and artifact hash.
9. Tear down synthetic services/data. Confirm hosted, stakeholder, and production gates remain
   unchanged.

## Operations runbook

### Provider unavailable

Return generic retryable 503 responses; do not fall back to development JWT or local password
verification. Preserve existing safe sessions only while server validation remains possible.
Escalate technical outage to Nathan and record correlation/timing without secrets.

### Suspected session or refresh compromise

Revoke the session/account family, rotate credentials/keys through controlled procedures,
inspect security events, notify the role-appropriate owner, and require fresh authentication.
Refresh-token reuse is treated as compromise, not retried indefinitely.

### Lost MFA / privileged recovery

Use recovery code first. Otherwise initiate the approved two-person, evidence-backed,
cooling-period flow. Neither subject nor operator may silently self-recover. After completion,
revoke sessions and require factor re-enrollment.

### Suspension/offboarding

Record reason, suspend identity, end memberships/assignments/delegations, revoke sessions and
credentials, transfer unresolved work, preserve immutable history, and verify direct API denial.
Restoration requires explicit new authority.

### Invitation or provider partial failure

Do not leave usable orphan authority. Revoke failed invitations and delete newly created
provider users where activation did not commit. Reconcile provider subject to PerchPoint
identity before retry.

### RLS or authorization anomaly

Deny access, preserve request/correlation and safe audit detail, stop affected processing,
reproduce using runtime credentials, and escalate to Nathan. Never bypass RLS to keep operations
moving.

## Acceptance checklist

Local acceptance requires all P6-R0–P6-R16 criteria applicable to local work, complete
current-commit evidence, no unexplained skips, clean-room reproduction, three-browser/manual
accessibility evidence, three-round benchmark evidence, independent review/remediation, and
merged canonical Git/CI verification. Nathan records technical acceptance only after those
conditions pass.

Hosted Supabase, Faruk/Ann stakeholder acceptance, specialist reviews, real-user onboarding,
production secrets, and production launch remain `BLOCKED_EXTERNAL` and cannot be inferred from
local success.

Requirements: `PP-ACCEPT-001`, `PP-ACCEPT-002`, `PP-ACCEPT-003`, `PP-AUTH-001`,
`PP-AUTH-002`, `PP-DATA-007`, `PP-PROV-002`, `PP-SEC-001`, `PP-NFR-001`,
`PP-NFR-002`.

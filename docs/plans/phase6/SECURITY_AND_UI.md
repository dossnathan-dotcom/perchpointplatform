# Phase 6 security, events, UI, and accessibility

## Threat model

Protected assets include credentials, sessions, recovery material, identity/contact history,
memberships/scopes/delegations, household/vendor relationships, restricted fields, private
documents, exports, security events, and authority decisions.

Primary threat actors and failure modes are an unauthenticated attacker, compromised ordinary
account, malicious insider, over-privileged vendor, confused-deputy worker/service principal,
stale session, replayed invitation/reset/refresh/API token, forged tenant headers, guessed IDs,
cross-organization queries, cache/search/export/storage leakage, threshold splitting, and
operator error during recovery/offboarding.

| Threat | Required control | Verification target |
| --- | --- | --- |
| Account enumeration/credential stuffing | Generic responses; layered account/IP/global controls; compromised-password deny | Negative auth and rate-limit cases |
| Session theft/CSRF | Opaque HttpOnly cookie; SameSite; Secure in hosted modes; CSRF token plus origin allowlist | Cookie, missing/mismatched CSRF, forged-origin tests |
| Stale or replayed authority | Current membership/policy checks; rotation; refresh-reuse revocation; expiry | Stale-role, expiry, reuse, revocation tests |
| Tenant/relationship escape | Transaction-local context; forced RLS; relationship policies; no trusted client headers | Cross-org/household/vendor/guessed-ID direct tests |
| Privilege escalation | Capability policy; AAL2/recent step-up; no self-grant/approval/recovery; role separation | Direct API escalation tests |
| Delegation/spend abuse | Non-transitive bounded grant; owner reservations; usage ledger; split aggregation | Boundary, scope, amount, replay, split tests |
| Data exfiltration | Field capabilities; private storage; authorized search/export/cache; audit | Restricted-field and alternate-channel tests |
| Machine/provider replay | Scoped expiring credentials; signed webhooks; idempotent inbox/outbox | Rotation, signature, timestamp, replay tests |
| Sensitive logging | Prohibit passwords, tokens, TOTP seeds, recovery/API codes, bank data | Log/payload scan |
| Unsafe lifecycle | Immediate session/access revocation; immutable history; work transfer | Suspension/offboarding/recovery tests |

Residual risk remains until complete adversarial, browser, clean-room, hosted, monitoring, and
recovery evidence exists.

## Security events and alerts

Auditable events include registration/invitation/verification/sign-in, MFA/recovery/reset/
contact/session changes, suspension/restoration/closure, role/scope/delegation/access request/
review, service credentials, denials, owner approvals, policy changes, sensitive reads, exports,
documents, support views, financial actions, and legal/adverse operations.

An event should preserve organization, actor/subject, action, outcome/reason, request/correlation,
resource/classification, role/bundle/scope/delegation/approval, AAL, policy version, timestamp,
and safe metadata. It must not include passwords, raw tokens, seeds, recovery/API credentials,
full bank data, or unnecessary sensitive content.

Technical alerts route to Nathan; owner-authority and major-account-risk alerts route to Faruk;
relevant staff/vendor operational alerts route to Ann. Routing is a policy requirement, not
evidence that alert delivery has been executed.

## Connected UI

The Phase 6 UI provides unified sign-in, MFA setup, onboarding/access summary, Security Center,
Users and Access, Delegation Center, access requests, access reviews, vendor access, maintenance
history, access-denied, and session-expired states. It displays server-derived organization,
membership role, scope summary, and assurance. Context switching calls the server.

Every workflow must represent loading, empty, error, denied, and unavailable states. Controls
whose API is absent explain that limitation; there are no placeholder successes. Denials avoid
confirming sensitive existence, expose a safe correlation ID, and link to an appropriate access
request. Near-expiry warnings do not extend server authority. Only explicitly safe,
non-sensitive drafts may remain in per-tab session storage.

## Accessibility acceptance

Critical identity/access journeys must be manually verified in Chromium, Firefox, and WebKit at
desktop and narrow viewport sizes. Required checks:

- keyboard-only order, activation, context switching, dialogs, forms, error recovery, and
  session warnings;
- visible focus, focus moved to submitted error summaries, no keyboard traps, and skip/main
  navigation;
- programmatic labels, headings, status/alert announcements, meaningful link/button names, and
  screen-reader interpretation of context/expiry/denial;
- zoom/reflow, touch targets, contrast, orientation, and no horizontal loss of task content;
- reduced motion and no time-only communication without warning/recovery;
- loading, empty, error, denied, unavailable, offline/provider failure, and stale-session paths.

Automated accessibility scans and component tests are useful evidence but do not certify WCAG
2.2 AA. The current component tests cover correlation IDs, denial request paths, and honest
onboarding unavailable states; three-browser and assistive-technology evidence remains
unexecuted.

Requirements: `PP-AUTH-001`, `PP-SEC-001`, `PP-SEC-003`, `PP-SEC-004`,
`PP-DATA-004`, `PP-PROV-002`, `PP-NFR-001`, `PP-NFR-002`, `PP-ACCEPT-001`.

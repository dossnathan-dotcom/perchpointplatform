# Phase 4 acceptance

## Remediation status

The acceptance recorded below for pull request 16 was provisional. Required automated visual, browser, Lighthouse, responsive, zoom, forced-color, reduced-motion, accessibility-tree, font, image, and CSP evidence had not been executed. That provisional status applied until closeout pull request 18 merged and the merged-main workflow passed. Do not treat the historical pull request 16 result as definitive local technical acceptance.

## Performance remediation status

The acceptance recorded for pull request 19 treated failed public Lighthouse floors as an accepted client-rendering constraint. That was incorrect. The floors stayed in force. Local three-run medians on the production static server now pass them: public desktop performance 100, LCP 0.593 s, TBT 0 ms; public mobile performance 99, LCP 1.995 s, TBT 13 ms; listing performance 99, LCP 2.194 s. Accessibility stayed 100, best practices stayed at least 95, public SEO stayed at least 95, and CLS stayed at or below 0.1. The same gate runs in the `phase4-performance` job. Definitive acceptance of this remediation is the merge of that passing job, not a lowered threshold.

```text
Phase 4 functional/design/accessibility/security implementation: passed
Phase 4 public performance acceptance: passed on local controlled medians
Phase 4 definitive local technical acceptance: pending the required CI performance job on this change
Hosted operational validation: owner-deferred
Production readiness: blocked
Phase 5: unauthorized
```

## Earlier closeout record

Closeout pull request 18 merged as `df4cc33759a136181e3b96c4bb0d39544b9550bf`. The merged-main workflow passed: https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36274778554

```text
Phase 4 core implementation: merged
Phase 4 definitive local technical acceptance: granted
Hosted operational validation: owner-deferred
Production readiness: blocked
Phase 5: unauthorized
```

That grant covered the executed design, accessibility, browser, and security gates. It does not remain the performance decision. Public Lighthouse on that commit was desktop performance 36, LCP 8.06 s, TBT 2412 ms, and mobile performance 75, LCP 6.81 s, TBT 117 ms. Those figures failed the approved floors. Bundle budgets passed. Automated accessibility, best practices, and public SEO scored 100, and CLS stayed at or below 0.1.

Human NVDA, VoiceOver, Faruk’s brand review, Ann’s operational review, hosted staging, and production accessibility certification remain pre-production deferred.

## Historical provisional record

Local technical acceptance requires the Phase 4 branch to pass governance, backend, frontend, browser, contracts, secrets, supply-chain, containers, and CodeQL, with the design-system tests and bundle budget included.

Those checks passed on pull request 16 head `1587bf9f448f3543b45156352938373f6abaff76` and again on the merged main commit `108949af86089ec97047d05ac7acbda7a0361ddb`.

- Pull request: https://github.com/dossnathan-dotcom/perchpointplatform/pull/16
- Head workflow: https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36266549854
- Merged main workflow: https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36266762796

Ann and Faruk have not been asked to accept the synthetic shells. That review is owner-deferred and does not block local engineering.

Production deployment, paid providers, real tenant data, and Phase 5 are not accepted and were not started.

Hosted operational validation remains deferred under PP-DEC-059. Human NVDA and VoiceOver transcripts remain pre-production deferred. Automated Lighthouse, Firefox, WebKit, and visual regression are closeout gates, not owner deferrals.


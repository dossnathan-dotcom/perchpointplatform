# Configurable delegation / approval contract

Source: `DelegationPolicy`, `Delegation`, `ApprovalRequest`, `ApprovalDecision` in `backend/foundation/delegation.py`.

Policy version and effective/expiry times are explicit. Seed thresholds are **$250 staff, $500 parts, 1× unit monthly rent**, awaiting Farouk’s approval. They are data, not a hard-coded application authorization threshold. No policy or approval is persisted or executed.

Request dimensions: decision type, expense category, requested amount, cumulative amount including this request for the same issue, unit monthly rent, approved remaining property/project budget, organization/property/building/unit scope, requester, assigned approver, vendor, emergency status, evidence, prior approvals, legal/compliance sensitivity and revision. Delegation adds delegate/grantor, permitted decisions/categories, maximum value, scope, effective/expiry dates, temporary flag and accepted policy version.

## Offline evaluation order
1. Deny self-approval and actor/assigned-delegate mismatch.
2. Deny expired/not-yet-effective grants or policies; deny silent policy-version changes.
3. Deny mismatched location scope, mixed currencies, cumulative totals excluding the request, disallowed decision/category.
4. If consuming a decision, compare request ID, revision, SHA-256 material fingerprint, policy version, actor and expected decision version.
5. Escalate legal or reserved lease/applicant/legal matters to Farouk.
6. Require supporting evidence.
7. A designated protective emergency can return an exception requiring immediate notification and retrospective review. This is **not financial approval** and sends nothing.
8. Deny values above delegated cumulative authority. Escalate unknown/exceeded budgets or repair totals above configured rent comparison to owner.
9. Escalate values above configured parts/staff thresholds; otherwise mark eligible for independent approval.

## Prevention contracts
- Self-approval: actor cannot equal requester, even for emergency authorization simulation.
- Expiry/scope/value: evaluated before normal grant.
- Material change: fingerprint and revision invalidate reuse; regenerate approval after change.
- Concurrent decisions: `expected_version` is the future compare-and-swap key; database transaction/unique decision constraint still required.
- Policy mutation: create a new version; explicit acceptance, immutable policy history and audit required before production.
- No shared approval codes: named, verified actor + step-up assurance and record-bound decision only.
- No approval reuse: request/decision idempotency and atomic consumption need future storage implementation.

Vendor, prior approvals, budget source and evidence are represented but not externally verified. No exchange-rate or legal interpretation engine exists. Emergency conditions and notification/review times need Farouk/legal/security approval.
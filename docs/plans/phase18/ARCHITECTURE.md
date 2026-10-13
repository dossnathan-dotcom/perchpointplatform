# Phase 18 architecture

Recorded October 12, 2026. This is the local implementation, not production activation.

## Phase 17 base

Phase 17 local acceptance is granted in `test_reports/phase17/acceptance-state.json`.

- Behavior revision: `a38223061e61d700ed9d590316f56e90eb19af09`
- Pull request 44 head: `2646aad42636525b4dea06fc26983928386d1978`
- Protected merge: `a68b28897d4f61abe6dd09ad78535214461acb66`
- Evidence commit on main: `a8c494dd479c7645da0b1d95ca3d6a53fb1a9561`
- Phase 17 migration head: `0060_phase17_grant_accept`

Phase 18 does not rewrite that evidence. The Phase 17 clean-room and predecessor scripts now stop at `0060_phase17_grant_accept` so a later migration does not make them claim a new head.

## Scope

`CONFLICT-027` replaces physical payment intake with digital receipts and housing assistance. Cash, check, and money-order commands are rejected. A historical import can keep a physical method only inside the staged import, and it cannot be applied as a new operational receipt.

## Financial boundary

The Phase 16 ledger remains the authority. An approved HCV split publishes a resident charge for the resident portion only. The agency portion is expected assistance until a confirmed digital receipt posts one subsidy journal. A remittance advice without a bank receipt does not post. A batch stores gross assistance, a source-linked recoupment, and the net cash receipt as separate numbers.

Stripe cash-balance funding and a payout to the bank are observations. They do not create a resident settlement. The resident settlement remains the existing Phase 17 payment application. Cash App Pay is a Stripe method on that same checkout path. A bank transfer returns synthetic instructions and does not create a debit mandate. Zelle stays unavailable.

A resident transfer report creates a case. It does not post a payment.

The ordinary refund cap is unchanged for tenancies without an assistance determination. When an approved determination exists, the ordinary maximum is also limited by that version's resident rent-to-owner portion. Already posted Phase 17 refund rows are not rewritten.

## Application

Exact agency cash posts only when the source is confirmed, the household and period are unambiguous, the purpose is rent assistance, and the amount equals the remaining agency portion. The rule version is `phase18-exact-v1`. Anything else stays unmatched or in review.

The Phase 17 worker applies queued receipts in the same process. `PHASE18_WORKER_ONCE=1` applies queued receipts and returns, so that test pass does not dispatch autopay or apply provider events. Row-level batch application leaves unresolved lines unposted.

## Local boundary

`real_values_activated` stays false. `money_moved` stays false. PBV and PBRA are labeled not configured. The collecting entity is the provisional HawkVision LLC label.

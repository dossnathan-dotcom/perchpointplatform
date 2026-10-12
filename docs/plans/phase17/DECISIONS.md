# Phase 17 decisions

Reference review date: October 11, 2026. These are implementation dispositions for the local synthetic product. They are not production activation, a Stripe account approval, or a legal conclusion.

## Explicit decisions

Q1. One provisional HawkVision LLC collection entity. Deposit, rent, prepayment, subsidy, and fee positions stay distinct. Legal name, bank destination, and deposit treatment are activation inputs.

Q2. Direct Stripe for one collecting business. ACH-shaped and card-shaped synthetic methods are demonstrated. No resident surcharge. Processor expense is a separate journal category and is not charged to the resident in the demonstration policy.

Q3. A published charge is payable immediately. A draft is not. The technical operator receives `payment.charge` only. That role does not receive refund or owner-exception authority.

Q4. At most one active additional payer per tenancy, with an expiring single-use invitation. The payer does not become a resident or a refund approver.

Q5. Partial and advance amounts are allowed. The server quotes the eligible amount. A partial payment does not change the lease or the due date.

Q6. Autopay enrollment stores a cap, a day of month, and `America/New_York`. The default collects only the eligible recurring remainder. An amount above the cap is an exception, not a silent partial charge. The enrollment tables exist; the scheduled worker is not yet a running process.

Q7. Processing amounts are separate from confirmed payments. An active collection reservation blocks a second collection of the same obligation.

Q8. Automatic retry is off. A timeout is reconciled through the same idempotency key. The local adapter remembers an accepted result so a fresh key is not used as recovery.

Q9. Ann's ordinary refund authority is one month of that tenancy's rent per request and as a cumulative monthly maximum. The limit is shared across payments, operators, and payers.

Q10. Obligation complaints stay on the Phase 16 dispute record. Processor disputes are separate `processor_disputes` rows.

Q11. Receipts and notices are synthetic and local. No email or SMS is sent.

Q12. The owner workspace lists refund cases waiting for an exact decision. Ordinary successful payments are not owner approvals.

## Engineering interpretations

- The anti-splitting rule is both the calendar month in `America/New_York` and a rolling 31-day window. This rolling check is configurable for final activation and is shown in the allowance response.
- The rent ceiling is the lesser of the period snapshot and the current monthly rent. A mid-month increase does not replenish the snapshot.
- Unresolved refund exposure remains reserved across month boundaries.
- An owner exception approves one exact case and does not reset the ordinary cap.
- Phase 16 `POST /api/v2/leasing/ledger/payments` still refuses live collection. Phase 17 uses `/api/v2/payments/*` and posts settlements, refunds, and returns through the existing journal with `money_moved = false`.

## Provisional values

HawkVision LLC is a synthetic entity code `hawkvision-llc`. Fee responsibility, subsidized-rent basis, nonmonthly leases, Stripe Dashboard permissions, and production timing remain activation inputs. `real_values_activated` stays false.

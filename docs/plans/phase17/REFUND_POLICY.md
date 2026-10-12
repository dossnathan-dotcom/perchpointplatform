# Phase 17 refund allowance

Scope: one tenancy, not one person, card, employee, or request. Amounts are USD minor units.

```
ceiling = min(period_snapshot_rent, current_monthly_rent)
calendar_remaining = max(0, ceiling - calendar_exposure)
rolling_remaining = max(0, ceiling - rolling_exposure)
ordinary_max = max(0, min(ceiling, calendar_remaining, rolling_remaining, source_remaining))
```

Calendar exposure is the organization's month in `America/New_York`. Rolling exposure is `(now - 31 days, now]`. Reserved, dispatched, pending, and unknown refunds count in both windows regardless of age. A succeeded refund counts only when its authorization falls in that window. Failed, canceled, rejected, and draft refunds do not count.

The server clock decides the window. The browser cannot choose the month.

An ordinary approval is allowed only when the requested amount is less than or equal to `ordinary_max`. The check runs in the transaction that locks `tenancy_refund_budgets`. A larger request is stored as `owner_decision_required` and does not consume allowance until an owner records an exact exception.

An owner exception must match the case amount and a written reason. It does not change the snapshot or clear prior usage.

A refund of a posted settlement debits receivable for the applied portion and prepayment for any unapplied portion, and credits the unapplied settlement bucket. The original settlement row is not edited. If the account period is closed, the correction is posted to a new open period.

No local refund moves money. Provider acceptance is not a credit on the payer's bank statement.

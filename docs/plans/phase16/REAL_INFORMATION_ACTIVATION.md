# Phase 16 real-information activation

This extends the Phase 15 manifest. It does not create a second onboarding process, and it does not activate real values.

| Class | Examples | Rule |
| --- | --- | --- |
| Business configuration | Entity display name, category labels, statement support route | Editable later without a source change. Stays synthetic now. |
| Restricted policy | Proration, allocation order, grace, write-off threshold, deposit interest | Requires Faruk Atmaca for accounting policy before activation. |
| Legal and accounting approval | Statement disclosures, fiscal close, qualified accounting review | Blocked until a qualified verdict exists. |
| Migration data | Opening balances, deposits, prepayments, assistance shares, cutoff date | Dry run only. Control totals must reconcile before any later activation. |
| Deployment settings | Fiscal calendar, export destination, delivery channel | Not a production setting in this phase. |
| Server-only secrets | Processor keys, bank credentials, webhook secrets | Rejected by the manifest. Never stored in a ledger row. |

No organization, resident, balance, bank, processor, chart, or provider value from outside the repository was requested or loaded. `real_values_activated` remains false.

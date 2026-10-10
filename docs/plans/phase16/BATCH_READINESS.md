# Phase 16 batch readiness

No real values were requested or activated. These rows extend the Phase 15 batch. They are not a separate onboarding process.

| Placeholder | Owner | Rule | Destination | Later gate |
| --- | --- | --- | --- | --- |
| Example Homes entity | Faruk Atmaca | Fictional entity code | Resident account | Real entity roster |
| 140000 minor-unit sample | Faruk Atmaca | Integer minor units | Journal charge | Opening-balance batch |
| Subsidy share | Faruk Atmaca | Does not become resident debt | Subsidy journal lines | Assistance roster |
| Deposit hold | Faruk Atmaca | Not applied to rent and not income | Deposit journal lines | Deposit policy review |
| Synthetic settlement | Nathan | Applied plus unapplied equals source | Allocation row | Phase 17 processor |
| Statement marker | Nathan | Marker must survive the statement body | Statement version | Qualified accounting review |
| Period 2026-10 | Ann Springer | Close blocks later posts for that account | Accounting period | Fiscal calendar approval |
| Opening manifest | Nathan | Dry run only | `ledger_manifest_runs` | Real-information batch |

`python scripts/phase16_demo.py --verify` checks this packet on a local target and reports `real_values_activated=false`.

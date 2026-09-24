# System of Record Map

| Domain | Operational authority | External authority |
|---|---|---|
| Property/party/work/decision history | PerchPoint | Government/legal records where applicable |
| Listing/availability/application entry | PerchPoint/HawkVision site | None in target model |
| Charges/allocations/balances/receipts | PerchPoint operational subledger | Formal accounting for GL/close |
| Payment execution | PerchPoint intent/exception | Stripe/bank settlement state |
| Screening | PerchPoint consent/order/decision audit | Provider report; human final decision |
| Signatures | PerchPoint packet/lifecycle/hash | E-sign execution evidence |
| Communications | PerchPoint routing/history/consent | Transport delivery state |
| Migration | PerchPoint staging/lineage/reconciliation | Innago archive as historical evidence |

Provider IDs never replace stable PerchPoint IDs.
Organization, jurisdiction, property, party, money, and policy authority must remain explicit so
additional cities and states can be added without redesigning core identity or records.

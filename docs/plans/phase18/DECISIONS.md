# Phase 18 decisions

Recorded October 12, 2026 from the approved customization direction. These are local implementation dispositions. They are not quotes from Faruk or Ann, and they are not production activation.

Labels: U explicit user direction, I inherited approved direction, D delegated default, A deferred real-world confirmation.

Phase 17 local acceptance, the protected merge, and the merged-main checks are recorded in `test_reports/phase17/acceptance-state.json`. Phase 18 behavior starts from that base. This file does not activate real collection.

## Scope change

The saved roadmap called Phase 18 “Cash exceptions and Innago coexistence” and included cash, check, and manual physical intake. That physical-collection scope is rejected. See `CONFLICT-027` in `docs/source/provenance/SOURCE_CONFLICT_REGISTER.md`.

Phase 18 now covers centralized digital receipt evidence, housing-assistance remittances, exception resolution, and controlled historical import. It keeps unknown money, evidence, duplicate prevention, approval controls, historical corrections, opening-balance staging, and the illustrative $1,975 legacy digital receipt.

Phase 19 keeps broader bank and payout reconciliation, account-wide closing, accounting exports, and formal accounting expansion. Maintenance intake stays in its later roadmap phase. Old physical-intake requirements are not marked implemented.

`real_values_activated` stays false. `money_moved` stays false.

## Questions

| ID | Label | Disposition |
| --- | --- | --- |
| Q01 | U/D/A | No new cash, checks, money orders, or physical collection. Prefer Stripe methods, including eligible Cash App Pay and bank-payment flows. Agency direct deposits and approved business-bank transfers are digital sources. Zelle is conditional and stays unavailable without a supported evidence path. |
| Q02 | U | Physical custody is out of scope. Ann matches routine digital evidence. Technical staff maintain integrations. An independently authorized reviewer handles sensitive exceptions. Maintenance staff have no collection authority. |
| Q03 | D | A resident may report an already-sent digital transfer. The report is unverified, opens a case, and is not a payment or a collection hold. Bank or provider evidence confirms funds. Staff may attach versioned agency notices. |
| Q04 | I/D | Separate reported, source-confirmed, reserved, posted, and reversed states. Confirmed funds can reserve a remaining obligation. A claim alone cannot zero a balance or suppress collection indefinitely. |
| Q05 | I/D | One active designated additional payer per tenancy remains. An assistance remittance is a separate source, not a second portal member. One agency deposit may fund several households. A sponsor receipt needs explicit allocation evidence. |
| Q06 | I/D | Exact matching from an approved source follows published policy. Reassigning a posted receipt, overriding a source restriction, changing a destination, approving an opening balance, and material exceptions need independent review. Ordinary agency receipts are not owner approvals. |
| Q07 | D/A | Ann owns the operational queue. Nathan owns connector faults without receiving financial approval from that role. Provisional first-review target is two business days, with an organization calendar and escalation. |
| Q08 | I/D/A | Stage, validate, detect duplicates, preview, approve, and keep source lineage. Prefer transaction history. An opening balance is a separate approved import with a cutoff. Real migration stays a later gate. |
| Q09 | U/I/D | One digital-payments view: resident receivables, assistance expected, assistance received, unmatched confirmed funds, aging, returns, allocation exceptions, and decisions. No physical-cash custody widgets. Include the $1,975 legacy digital receipt. |
| Q10 | U/I/A | Provisional collecting entity is HawkVision LLC. Property and restricted-fund attribution stay distinct. Legal entity, account ownership, and bank destinations are activation inputs. |
| Q11 | D | Stripe is not required for every dollar. Agency deposits may arrive at an approved business bank. Do not manufacture a Stripe charge for money the bank already received. |
| Q12 | U/D/A | Cash App Pay uses the existing Stripe adapter, with capability-aware consent and recurring-contract coverage. Live eligibility stays an activation check. No automatic instrument switching. |
| Q13 | U/D | Bank debit and customer-initiated bank transfer are separate choices. A push transfer does not create a debit mandate. Prefer app-controlled application of Stripe cash balances when automatic allocation could violate a restriction. |
| Q14 | D/A | The live Zelle lane stays unavailable with an honest configuration reason. The adapter contract and synthetic bank-evidence import still exist. |
| Q15 | I/A | No resident-added processing surcharge in the local default. Processor expense stays separate from rent and assistance. |
| Q16 | U/D | An uploaded digital bank statement is reconciliation evidence, not a physical payment channel. Historical physical receipts keep their original method inside migration staging. |
| Q17 | U/D/A | Implement a synthetic tenant-based HCV path with explicit agency and program identity. PBV, PBRA, and other programs need their own configuration and are not implied by a generic subsidy flag. |
| Q18 | D/A | Track enrollment, payee reference, agreement and lease links, submission status, rent schedule, effective dates, and payment-setup readiness. Readiness is not a cash receipt. |
| Q19 | D | A verified agency notice or approved agreement is authoritative. The application validates structured values and records review. It does not estimate tenant responsibility from income. |
| Q20 | D | A late agency amount stays an assistance exception. It is excluded from resident arrears, late fees, autopay, and adverse housing actions. |
| Q21 | D/A | Rent-to-owner, utility allowance, and utility reimbursement stay distinct. No household-benefit disbursement engine in this phase. |
| Q22 | D | A revision is a new determination version. Differences are previewed and posted as append-only adjustments. A larger amount does not expand autopay consent. |
| Q23 | D/A | End a schedule on its effective date. Do not carry assistance to another home or charge full contract rent only because an integration stopped. |
| Q24 | D | Withheld, abated, suspended, and recouped assistance use explicit categories. Expected-but-late is not the same as no longer payable. |
| Q25 | D/A | No universal agency portal or API. Supported feeds, exports, and a secure import path. No portal scraping or shared passwords. A synthetic fixture is not a certified CMHA export. |
| Q26 | D | One remittance batch may cover several households and months. Unresolved lines do not post. |
| Q27 | D | Gross assistance, source-linked recoupment, and net deposit are separate and must reconcile. |
| Q28 | D | A resident sees their approved portion, effective date, own payments, and a concise assistance status. Other households and internal disputes stay hidden. |
| Q29 | U/I/D/A | Link notices, addenda, sample remittances, and the household lease in the existing document system. Official text is not rewritten. Synthetic companions stay marked. Sample leases keep the existing non-execution marker. |
| Q30 | D | Economic identity uses source transaction identity, receiving-account scope, provider and environment, revisions, and allocation lineage. A file hash is not economic uniqueness. A remittance and its bank deposit are one economic effect. |
| Q31 | D | Automatic posting requires a trusted confirmed source, compatible entity, currency, and recipient, one tenancy and period, a permitted purpose, no competing allocation, no unresolved revision or hold, and exact conservation. Fuzzy similarity never posts. |
| Q32 | D | Unidentified confirmed funds stay in a restricted unallocated position. The system does not guess a tenant or type an independent balance. |
| Q33 | I/D | A resident claim is only a case. A verified source or approved hold changes collectible amounts through the Phase 17 reservation path. An already-submitted debit is reconciled, not promised cancelled. |
| Q34 | I/D | Assistance cannot silently pay a deposit, fee, unrelated household, or non-rent obligation. |
| Q35 | D | Destination changes and posted-match corrections are sensitive. Correct a posted match with a linked reversal and reallocation. |
| Q36 | I/D/A | Keep the Phase 17 refund limits. For assisted tenancies, the local ordinary refund basis is the tenant rent-to-owner contribution, excluding the agency portion, utilities, fees, and deposits. A missing basis requires review. Already-posted Phase 17 refund history is not rewritten. Final program review is an activation item. |
| Q37 | D/A | Discretionary refunds, processor reversals, and agency recoupments stay distinct. A mandatory return is not an ordinary-cap bypass checkbox. Agency funds return to the entitled source. |
| Q38 | U/I | The Phase 17 tenancy refund budget is shared across Phase 18 digital sources. Separate channel allowances are not created. |
| Q39 | I/D/A | Use the configured organization timezone and business calendar. Store value date, observed time, effective period, posting time, and review time separately. Freeze clocks in evidence. |
| Q40 | D | A stale feed exposes its last observation and pauses unsafe allocation for the disputed portion. It is not treated as zero debt or confirmed eligibility. |
| Q41 | I/D | Integration health and replay are separate from financial approval. A platform administrator login is not financial authority. |
| Q42 | U/D | Authorized settings cover methods, source mappings, agency profiles, evidence requirements, alert routing, review targets, templates, and allocation policy versions. Users do not type raw identifiers to match a remittance. |
| Q43 | U/I/D | Keep the 20 presentation homes and 20 households. Use six of those households for the November 2026 assistance demonstration unless an existing fixture already maps an equivalent set. |
| Q44 | I/D | Private organization storage, bounded uploads, checksums, retention class, and redacted ordinary screens. No real SSNs, bank credentials, or tax forms in local proof. |
| Q45 | U/I/D | Use the shared shell, accessible forms, and working flows. A displayed capability is either operable or clearly an activation requirement. |
| Q46 | I/D | Local outbox and Mailpit for receipts, allocation updates, required actions, failures, and assistance follow-up. Routine matches do not notify Faruk. |
| Q47 | D | Measure the steps to import a repeat batch, review matches, resolve one exception, and trace a figure to its source. Do not invent an automation rate. |
| Q48 | I/D | Draft mappings can change before application. Posted effects use compensating entries. A retry is not a fresh payment. |
| Q49 | I/D | The phase is finished only when the local scope, evidence, review, and authorized protected release path are complete on the running product. |

## Activation boundary

Exact legal entity, bank destinations, Stripe method eligibility, Cash App eligibility, Zelle availability, the real PHA list, official schedules, refund-basis approval, and the no-physical-payment policy against real agreements stay in the consolidated activation register. They use synthetic stand-ins locally.

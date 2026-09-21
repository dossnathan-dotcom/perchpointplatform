# Provider-neutral registry, screening and payment contracts

No provider SDK, credential, webhook receiver, money movement, screening order, document upload, email/SMS delivery, signing or AI/model call is added.

## Registry
`IntegrationRecord` covers payments, screening, e-signature, voice/SMS, transactional email, calendar, listing distribution, accounting/banking, file storage and AI/model providers. Each synthetic registry entry is disconnected, not configured, with null credential reference and zero supported live capabilities.

Fields: provider type/name, environment, connection/configuration status, credential **reference**, capabilities, required webhook names, last successful sync/failure, retry/exception state, data ownership, mapping IDs, activation checklist, deactivation procedure, replacement procedure. Required webhook names are neutral placeholders—not claims about a selected provider API.

`ProviderAdapter.execute(AdapterCommand)` accepts organization, actor, correlation ID, operation, canonical record ID and idempotency key. The only implementation is `DisconnectedAdapter`: it always returns `accepted=false`, `status=disconnected`, `PHASE0_EXECUTION_DISABLED`, `side_effects=false`. No network access or retry worker exists.

`ExternalReference` separates integration/environment/provider-object identifiers from canonical PerchPoint resource UUIDs. Future uniqueness is `(organization, integration, environment, provider_object_type, provider_object_id)`. Replacement creates new mappings, never rewrites canonical IDs.

Activation must verify company ownership/recovery, approved scope, capabilities, webhook signatures, replay/idempotency, failure mapping, reconciliation, data export/deletion, legal terms and authorization/RLS. Deactivation pauses commands, reconciles outstanding events, revokes credentials and archives references. Replacement must validate new mappings, reconcile, approve cutover and retire the old system.

## Screening contract, not screening implementation
`ScreeningRecord`: applicant person, scope, permissible purpose, disclosure/criteria/retention/access-policy versions, consent reference, order/provider reference, status, minimal normalized result, restricted report document reference, human reviewer, recommendation record, Farouk final decision, adverse-action/dispute cases, provider callback, failure/retry state.
`ApplicantConsent`: individual person, disclosure version, purpose, time, evidence reference and withdrawal time.

Normalized result is deliberately minimal (`not_requested`, `human_review_required`, `provider_unavailable`). No raw report, score, criminal history, SSN, income or sensitive screening data is seeded. Recommendation/decision/adverse-action/dispute fields are future references, not automated behaviors. `autonomous_decision` must be false.

Human review and Farouk’s attributable final decision are separate gates. Counsel must approve permissible purpose, disclosures, criteria, notices, dispute support, adverse-action timing and retention before any screening provider is activated. No autonomous approval, rejection, ranking or adverse action is possible here.

## Payment contract, not financial execution
Records: `PaymentMethodReference`, `Charge`, `Allocation`, `PaymentRecord`, `PaymentException`, `AutopayConsent`, `ProviderEvent`.
Payment method stores only a provider-token mapping reference, not PAN/CVV/routing/bank numbers. Extra fields are forbidden by Pydantic.
Payment record tracks charge IDs/allocations, attempts, processor status, ledger posting status, settlement status/time, failure/ACH-return code, refund/dispute references, receipt document, autopay consent, reconciliation exception, idempotency and provider events.

**Browser success is not financial posting.** Processor success, ledger posting and bank settlement remain separate states. `browser_success_is_posting=false` is mandatory. No real balances or “rent collected” statistics are shown in the shells.
Future posting requires verified provider events, replay safety, atomic balanced ledger entries, explicit reconciliation and return/refund/dispute handling. Autopay needs attributable versioned consent, limits/frequency and revocation. No user can enter financial credentials or initiate a charge/refund in this iteration.

AI registry entry is inventory only, not permission to reintroduce AI/chat. Chat remains excluded unless separately requested.
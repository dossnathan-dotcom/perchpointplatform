# Phase 17 architecture

PerchPoint remains the obligation source. Stripe is an adapter with an injectable transport. The default transport is in-process, stores no card or bank number, and does not open a network connection. A mocked transport result is not a Stripe sandbox transaction.

Payment orders, attempts, collection reservations, refund cases, and journal lines are separate facts. A succeeded local card payment posts one Phase 16 settlement for the gross amount. Processor expense is a distinct category and is zero under the demonstration surcharge policy. `money_moved` remains false.

`POST /api/v2/leasing/ledger/payments` still returns the Phase 16 refusal. Phase 17 commands live under `/api/v2/payments`.

Idempotency keys are stored with a fingerprint. The same key and same intent replay. The same key with a changed amount or source is rejected. Provider timeout is marked `unknown` and reconciled from the original key.

The refund budget row is locked with `SELECT FOR UPDATE` before a reservation. Competing approvals share that row.

Callbacks require an HMAC of the raw body. They do not use browser CSRF, and ordinary commands still do. A signed delivery is stored on the application database before it is acknowledged. `process_provider_inbox` applies that delivery through the same settlement and return posting used by a verified provider result. Repeating a delivery, or sending another delivery for the same effect, does not post a second journal. Real Stripe webhooks are not connected.

The contract tests call `StripeAdapter` in `phase17_stripe.py`, which uses `stripe` 14.4.1 and API version `2026-02-25.clover`, with an injected HTTP client. Those tests do not open a network connection. Sandbox execution has not been run. Card PaymentIntents are the partial-refund path for the local $400/$700 demonstration. ACH partial refunds stay unavailable because Stripe's general method page and its ACH refund article disagree, and this phase does not pick the unresolved reading.

Production startup is not enabled. Merchant configuration cannot set `live_enabled` or `real_values_activated`.

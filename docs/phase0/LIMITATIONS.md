# Known limitations and architectural review gates

1. **MOCKED role shells**, provider adapters and operational queues; no production auth/MFA/RLS. UI selection is not identity or authorization.
2. Canonical schema/fixture validation runs in Python; no canonical database, SQL migration or database constraints are applied. MongoDB remains for synthetic capture only.
3. Future PostgreSQL RLS, service identity, transactional ledger/event/audit persistence, foreign keys and isolation are not tested or claimed complete.
4. Delegation is a pure simulation. It cannot verify evidence/vendors/budgets, consume a persisted approval atomically, lock competing decisions or send emergency notifications.
5. Screening/payment/signature/document/retention/audit/event records are contracts, not operational workflows. Restricted reports and financial credentials are absent.
6. Frozen models and report checksums are not immutable storage. Durable audit/WORM, migration rollback and outbox/inbox replay safety remain future work.
7. Legal rules, retention periods, jurisdiction precedence, screening/adverse-action notices and fees are intentionally unapproved.
8. Synthetic aggregate validation assumes complete property shapes; a future incremental property onboarding transaction needs a separate draft/staging contract.
9. UUID-based unit URLs replace legacy example slugs. No real brokerage data is retained or migrated.
10. The frontend remains primarily JavaScript. Type checking covers generated contracts and the typed API boundary; legacy JSX is built and linted, not fully statically typed.
11. Automated accessibility checks cannot certify WCAG conformance for every assistive technology. Retain manual keyboard/screen-reader/zoom review and verified real imagery before publication.
12. Feature flags remove labeled synthetic surfaces, not install a production experience. Bundled fixtures are public non-sensitive examples. Provider connectivity, live availability and real intake are not enabled by removing a label.

## Cursor / architecture review recommended before later phases
- PostgreSQL target schema, composite org/location foreign keys, uniqueness, RLS and field/document-level permissions.
- Person deduplication, historical relationship validity, business legal identities, signer/guarantor rights and account lifecycle.
- Canonical ledger model and atomic transactions involving approval/audit/domain event/outbox.
- Policy versioning, request fingerprinting, approval CAS/idempotency, emergency authority and support/impersonation separation.
- Migration manifest control totals, multiple currencies, correction provenance, document archives, reconciliation and cutover/rollback.
- Qualified legal review of jurisdiction overlays, retention/legal holds, screening and adverse action.
- Threat model and direct authorization/security tests once actual authentication is proposed.

This iteration does not authorize the next phase. Farouk must review the foundation and explicitly approve subsequent implementation scope.
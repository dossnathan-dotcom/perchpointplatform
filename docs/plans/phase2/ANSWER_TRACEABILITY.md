# Phase 2 answer traceability

Source register: [APPROVED_CUSTOMIZATION_ANSWERS.md](APPROVED_CUSTOMIZATION_ANSWERS.md).
Decision IDs are only those in [SCOPE_AND_DECISIONS.md](SCOPE_AND_DECISIONS.md). Requirement IDs are only those in [REQUIREMENTS_TRACEABILITY.md](../../governance/REQUIREMENTS_TRACEABILITY.md).

Answer coverage is not implementation coverage. `planned` means this package includes a contract or fixture check. `deferred` means a later package. `not evidence` means the decision is recorded and this package does not prove the capability.

| Question | Decisions | Requirements | Package | Evidence | Notes |
|---|---|---|---|---|---|
| Q1 | PP-P2-DEC-010 | PP-NFR-002; PP-AUTH-001 | P2-01 | planned | Modular-monolith decision recorded. No service extraction in this package. |
| Q2 | PP-P2-DEC-010 | PP-NFR-002; PP-AUTH-001 | P2-02 | deferred | PostgreSQL invariants are not P2-01 evidence. |
| Q3 | PP-P2-DEC-011 | PP-NFR-001 | P2-04 | deferred | Visual shell stays. No rewrite in P2-01. |
| Q4 | PP-P2-DEC-012 | PP-PROP-002; PP-SEC-003 | P2-01 | planned | One operating org plus a second synthetic org id for later deny tests. |
| Q5 | PP-P2-DEC-013 | PP-PROP-001; PP-PROP-005 | P2-01 | planned | Legal entity remains a relationship endpoint, not a property column rewrite. |
| Q6 | PP-P2-DEC-013 | PP-PROP-001; PP-PROP-005 | P2-01 | planned | Effective-dated ownership and management contract rows. |
| Q7 | PP-P2-DEC-013 | PP-PROP-001; PP-PROP-005 | P2-01 | planned | CONFLICT-008 relationship-first model. Not a rigid ownership tree. |
| Q8 | PP-P2-DEC-013 | PP-PROP-001 | P2-01 | planned | Existing mixed-use fixture retained. |
| Q9 | PP-P2-DEC-013 | PP-PROP-001 | P2-01 | planned | Common space core with exclusive residential or commercial terms. |
| Q10 | PP-P2-DEC-013 | PP-PROP-001; PP-PROP-005 | P2-01 | not evidence | Portfolio membership is modeled. Full tag catalog is not. |
| Q11 | PP-P2-DEC-009 | PP-AUTH-010 | P2-01 | planned | Phase 0 person graph reused. Authentication stays a separate record. |
| Q12 | PP-P2-DEC-013 | PP-LEASE-003 | P2-01 | planned | Existing business-party fixture. Full vendor CRM is later. |
| Q13 | PP-P2-DEC-009 | PP-AUTH-010; PP-AUTH-009 | P2-01 | planned | CONFLICT-010. One open primary portal account per household in the reference validator. |
| Q14 | PP-P2-DEC-013 | PP-LEASE-003 | P2-01 | planned | Existing relationship kinds distinguish occupant, signer, guarantor, and minor. |
| Q15 | PP-P2-DEC-013 | PP-DATA-004; PP-PROP-005 | P2-01 | planned | Ended relationship dates in fixtures. Retention enforcement is later. |
| Q16 | PP-P2-DEC-014 | PP-PROP-002 | P2-01 | planned | Existing fixture UUIDs preserved. No identity rewrite. |
| Q17 | PP-P2-DEC-014 | PP-PROP-002; PP-PROV-002 | P2-01 | planned | ExternalReference remains the mapping. Provider ids are not canonical keys. |
| Q18 | none | PP-PROP-005 | later/blocked | deferred | Normalized addresses exist. Issued-document snapshots are later. |
| Q19 | PP-P2-DEC-010 | PP-NFR-002 | P2-01 | not evidence | UTC instants and date-only fields are the contract convention. Time-zone persistence is not proven. |
| Q20 | PP-P2-DEC-015 | PP-FIN-001 | P2-01 | planned | Money stays integer minor units plus ISO currency. |
| Q21 | PP-P2-DEC-016 | PP-DATA-004; PP-GOV-002 | P2-01 | planned | Space-dimension guards are contract functions. Database enforcement is P2-02. |
| Q22 | PP-P2-DEC-016 | PP-DATA-004 | later/blocked | deferred | Property lifecycle vocabulary approved. Engine not in P2-01. |
| Q23 | PP-P2-DEC-016 | PP-DATA-004 | later/blocked | deferred | Building lifecycle vocabulary approved. Engine not in P2-01. |
| Q24 | PP-P2-DEC-016 | PP-DATA-004 | P2-01 | planned | CONFLICT-009 separated space dimensions and transition guards. |
| Q25 | PP-P2-DEC-016 | PP-DATA-004; PP-SEC-002 | later/blocked | deferred | People are not deleted by ending a relationship. Lifecycle engine is later. |
| Q26 | PP-P2-DEC-016 | PP-LEASE-003 | later/blocked | deferred | Household journey stays derived. No exclusive permanent status engine. |
| Q27 | PP-P2-DEC-016 | PP-WORK-001 | later/blocked | deferred | Contractor vocabulary approved. Transitions are later. |
| Q28 | PP-P2-DEC-016 | PP-WORK-003 | P2-01 | not evidence | Read-only task example only. Full ownership fields are not claimed. |
| Q29 | PP-P2-DEC-016 | PP-GOV-002 | P2-01 | not evidence | No workflow-engine dependency. Shared frameworks are later. |
| Q30 | PP-P2-DEC-016 | PP-GOV-002 | later/blocked | deferred | Admin configuration is later. Topology stays developer-controlled. |
| Q31 | PP-P2-DEC-018 | PP-DATA-004; PP-PROV-002 | later/blocked | deferred | Operational authority recorded. Reconciliation runtime is later. |
| Q32 | PP-P2-DEC-018 | PP-PROV-002 | P2-03 | deferred | Visible conflict exceptions are not implemented in P2-01. |
| Q33 | PP-P2-DEC-016 | PP-DATA-004 | P2-01 | not evidence | Phase 0 unit status projects into space dimensions. Derived balances are later. |
| Q34 | none | PP-SEC-002; PP-DATA-004 | later/blocked | deferred | No universal soft-delete added. |
| Q35 | PP-P2-DEC-016 | PP-DATA-004 | later/blocked | deferred | Correction records are later. P2-01 does not edit history in place. |
| Q36 | none | PP-SEC-001 | later/blocked | deferred | Classification vocabulary approved. Field catalog is later. |
| Q37 | none | PP-SEC-001 | later/blocked | deferred | Field-level treatment is later. |
| Q38 | none | PP-SEC-002; PP-PROV-002 | later/blocked | deferred | Screening storage stays provider-reference only until legal review. |
| Q39 | none | PP-SEC-001; PP-SEC-002 | later/blocked | deferred | Full government identifiers are not stored in P2-01. |
| Q40 | PP-P2-DEC-005 | PP-FIN-003 | later/blocked | deferred | No raw payment credentials. Processor is not activated. |
| Q41 | none | PP-SEC-002 | later/blocked | deferred | Retention periods remain unapproved. |
| Q42 | none | PP-SEC-002 | later/blocked | deferred | No automatic destructive retention in P2-01. |
| Q43 | none | PP-SEC-002 | later/blocked | deferred | Legal-hold workflow is later. |
| Q44 | PP-P2-DEC-018 | PP-SEC-001 | P2-03 | deferred | Sensitive-access audit runtime is not P2-01. |
| Q45 | none | PP-SEC-001 | later/blocked | deferred | Export controls are later. |
| Q46 | PP-P2-DEC-016; PP-P2-DEC-017 | PP-NFR-002 | P2-01 | planned | Command and read contracts only. No new HTTP routes. |
| Q47 | PP-P2-DEC-017 | PP-NFR-002 | P2-01 | planned | 0.2.0 types are additive. Phase 0 records stay 0.1.0. |
| Q48 | PP-P2-DEC-017 | PP-NFR-002 | P2-01 | planned | Pydantic export generates JSON Schema and TypeScript. |
| Q49 | PP-P2-DEC-016 | PP-DATA-004; PP-GOV-002 | P2-01 | planned | Material actions are explicit command types. |
| Q50 | PP-P2-DEC-016 | PP-NFR-002 | P2-01 | planned | Safe error envelope includes retryability and required action. No runtime handler. |
| Q51 | PP-P2-DEC-018 | PP-DATA-004 | P2-01 | planned | Idempotency key and fingerprint fields. Conflict behavior is P2-03. |
| Q52 | PP-P2-DEC-016 | PP-DATA-004 | P2-01 | planned | Expected-version field. Locking is P2-02 and P2-03. |
| Q53 | PP-P2-DEC-016 | PP-NFR-002 | P2-01 | planned | Cursor page contract. No list endpoint. |
| Q54 | PP-P2-DEC-019 | PP-AUTH-001 | P2-02 | deferred | Search authorization is not a P2-01 runtime. |
| Q55 | PP-P2-DEC-016 | PP-AUTH-001 | later/blocked | deferred | No bulk command in the reference slice. |
| Q56 | PP-P2-DEC-018 | PP-PROV-002 | P2-03 | deferred | Durable jobs are not introduced in P2-01. |
| Q57 | PP-P2-DEC-018 | PP-DATA-004 | P2-01 | planned | Versioned reference event types. Not full event sourcing. |
| Q58 | PP-P2-DEC-018 | PP-PROV-002; PP-DATA-004 | P2-03 | deferred | Outbox transaction is not executed in P2-01. |
| Q59 | PP-P2-DEC-018 | PP-PROV-002 | P2-03 | deferred | Inbox runtime is not P2-01. |
| Q60 | PP-P2-DEC-018 | PP-PROV-002 | P2-03 | deferred | At-least-once delivery is not claimed from model tests. |
| Q61 | PP-P2-DEC-017 | PP-NFR-002 | P2-01 | not evidence | Additive compatibility rule recorded. No consumer suite. |
| Q62 | PP-P2-DEC-018 | PP-DATA-004 | P2-01 | planned | Audit contract is distinct from activity notes. Storage is P2-03. |
| Q63 | PP-P2-DEC-018 | PP-SEC-001 | P2-03 | deferred | Full audit content is not persisted in P2-01. |
| Q64 | PP-P2-DEC-018 | PP-SEC-001 | P2-03 | deferred | Hash fields exist on the contract. Tamper evidence is not proven. |
| Q65 | PP-P2-DEC-018 | PP-PROV-002 | P2-03 | deferred | Replay without repeating the business decision is P2-03. |
| Q66 | PP-P2-DEC-006; PP-P2-DEC-007 | PP-AUTH-003; PP-COMM-005 | later/blocked | deferred | Dead-letter ownership is not a P2-01 queue. |
| Q67 | PP-P2-DEC-018 | PP-PROV-001; PP-PROV-002 | P2-01 | planned | Existing disconnected adapter ports. No provider activation. |
| Q68 | PP-P2-DEC-005 | PP-FIN-003; PP-PROV-001 | later/blocked | deferred | Stripe is not an activated dependency. |
| Q69 | PP-P2-DEC-018 | PP-PROV-002 | later/blocked | deferred | Provider-specific extensions are not added to the domain model. |
| Q70 | PP-P2-DEC-005 | PP-SEC-003 | P2-03 | deferred | Fake adapter contract only. No live calls. |
| Q71 | none | PP-SEC-001; PP-PROV-002 | P2-03 | deferred | Webhook secret isolation is later. |
| Q72 | none | PP-PROV-002 | later/blocked | deferred | Integration health surface is later. |
| Q73 | none | PP-COMM-001 | later/blocked | deferred | Conversation ownership is later. |
| Q74 | PP-P2-DEC-002 | PP-PROD-003 | later/blocked | deferred | No Zillow or Facebook connector. |
| Q75 | PP-P2-DEC-004 | PP-FIN-005; PP-FIN-001 | later/blocked | deferred | Operational accounting boundary recorded. No ledger engine. |
| Q76 | PP-P2-DEC-021 | PP-MAINT-008 | later/blocked | deferred | Maintenance app remains post-core. |
| Q77 | PP-P2-DEC-021 | PP-GOV-005 | P2-01 | planned | Reference contracts only. Leasing and approval engines excluded. |
| Q78 | PP-P2-DEC-012; PP-P2-DEC-014 | PP-DATA-002; PP-SEC-003 | P2-01 | planned | Existing property shapes kept. Relationship and space-state fixtures added. |
| Q79 | PP-P2-DEC-013 | PP-PROP-001 | P2-01 | planned | Elm Court bakery unit remains the synthetic mixed-use example. |
| Q80 | PP-P2-DEC-007; PP-P2-DEC-008 | PP-AUTH-005; PP-AUTH-006 | P2-04 | deferred | Personas map to existing roles later. P2-01 does not authenticate them. |
| Q81 | PP-P2-DEC-024 | PP-GOV-002 | later/blocked | deferred | Emergent work waits for a contract freeze. |
| Q82 | PP-P2-DEC-011 | PP-NFR-001 | P2-04 | deferred | No visual rewrite in P2-01. |
| Q83 | PP-P2-DEC-020 | PP-AUTH-001; PP-SEC-001 | P2-02 | deferred | Model tests do not prove PostgreSQL, RLS, or transactions. |
| Q84 | PP-P2-DEC-020 | PP-NFR-002 | P2-02 | deferred | No production Supabase or cloud activation. |
| Q85 | PP-P2-DEC-021 | PP-DATA-004 | P2-02 | deferred | Write contracts exist. Persistence, auth, audit, and events are later packages. |
| Q86 | PP-P2-DEC-021 | PP-ACCEPT-001 | P2-01 | planned | P2-01 covers contract rejection and projection cases only. Denial, concurrency, and outbox remain later. |
| Q87 | PP-P2-DEC-001 | PP-NFR-002 | P2-05 | deferred | No capacity claim from P2-01. |
| Q88 | none | PP-NFR-002 | later/blocked | deferred | Availability target is not an achieved SLA. |
| Q89 | none | PP-NFR-001; PP-NFR-002 | P2-05 | deferred | Performance targets are unmeasured. |
| Q90 | PP-P2-DEC-004 | PP-NFR-002; PP-FIN-001 | later/blocked | deferred | No restore proof. Transactions are not disaster recovery. |
| Q91 | PP-P2-DEC-011 | PP-NFR-001 | P2-04 | deferred | No UI journey in P2-01. |
| Q92 | PP-P2-DEC-011 | PP-NFR-001 | P2-04 | deferred | No browser certification in P2-01. |
| Q93 | PP-P2-DEC-016 | PP-NFR-001 | later/blocked | deferred | No offline authority. |
| Q94 | none | PP-NFR-002; PP-SEC-001 | later/blocked | deferred | Observability stack is later. |
| Q95 | PP-P2-DEC-006; PP-P2-DEC-007; PP-P2-DEC-008 | PP-AUTH-003; PP-AUTH-005; PP-AUTH-006 | later/blocked | deferred | Alert routing is not implemented. |
| Q96 | PP-P2-DEC-019; PP-P2-DEC-020 | PP-SEC-001 | P2-02 | deferred | Checklist is not certification. |
| Q97 | none | PP-SEC-001 | later/blocked | deferred | No rate limiter in P2-01. |
| Q98 | none | PP-SEC-001 | later/blocked | deferred | Residency is a hosting constraint for later infrastructure, not a new requirement. |
| Q99 | none | PP-SEC-001 | later/blocked | deferred | Log retention tiers are later. |
| Q100 | PP-P2-DEC-019 | PP-AUTH-001 | P2-02 | deferred | Flags do not grant authorization. No flag service in P2-01. |
| Q101 | PP-P2-DEC-021 | PP-ACCEPT-001 | P2-01 | planned | This package runs contract and fixture tests only. |
| Q102 | none | PP-ACCEPT-001; PP-FIN-001 | P2-05 | deferred | Property-based tests wait for the implemented behavior. |
| Q103 | none | PP-ACCEPT-001 | P2-05 | deferred | Mutation testing is not required in P2-01. |
| Q104 | PP-P2-DEC-017 | PP-NFR-002; PP-ACCEPT-001 | P2-01 | planned | Local export and TypeScript checks. Remote CI remains later. |
| Q105 | none | PP-NFR-002; PP-GOV-002 | P2-02 | deferred | No migration in P2-01. |
| Q106 | PP-P2-DEC-010 | PP-NFR-002 | P2-01 | not evidence | Planning diagrams already exist. They are not regenerated evidence. |
| Q107 | PP-P2-DEC-010; PP-P2-DEC-017; PP-P2-DEC-018; PP-P2-DEC-020 | PP-GOV-002 | P2-01 | not evidence | Existing ADRs reused. No new ADR required for this package. |
| Q108 | none | PP-ACCEPT-001; PP-NFR-002 | P2-05 | deferred | No load test in P2-01. |
| Q109 | PP-P2-DEC-020 | PP-SEC-001; PP-AUTH-001 | P2-02 | deferred | Threat tests for absent surfaces stay documented, not executed here. |
| Q110 | PP-P2-DEC-018 | PP-ACCEPT-001 | P2-03 | deferred | Failure simulation belongs to the worker package. |
| Q111 | PP-P2-DEC-007 | PP-AUTH-006 | later/blocked | not evidence | Technical ownership stays with Nathan. This file is not a new acceptance. |
| Q112 | PP-P2-DEC-001; PP-P2-DEC-008 | PP-ACCEPT-002 | later/blocked | deferred | Domain acceptance remains with the named authorities. |
| Q113 | PP-P2-DEC-025 | PP-ACCEPT-002 | later/blocked | not evidence | Provisional acceptance cannot replace legal, financial, or production approval. |
| Q114 | PP-P2-DEC-024; PP-P2-DEC-025 | PP-GOV-002 | P2-01 | not evidence | Work stays on cursor/phase-02-contracts. Other branches are not created here. |
| Q115 | PP-P2-DEC-024; PP-P2-DEC-025 | PP-GOV-002; PP-GOV-005 | later/blocked | deferred | Freeze and Emergent steps are after P2-01. |
| Q116 | PP-P2-DEC-024 | PP-GOV-002 | later/blocked | deferred | Emergent restrictions apply after freeze. |
| Q117 | PP-P2-DEC-001; PP-P2-DEC-021 | PP-GOV-005; PP-ACCEPT-001 | later/blocked | deferred | Full Phase 2 exit gate. P2-01 does not satisfy it. |
| Q118 | PP-P2-DEC-001 | PP-ACCEPT-002 | later/blocked | deferred | Business acceptance stays provisional. |
| Q119 | PP-P2-DEC-001 | PP-GOV-005; PP-AUTH-011 | later/blocked | deferred | Production remains blocked. |
| Q120 | PP-P2-DEC-025 | PP-ACCEPT-002; PP-GOV-002 | P2-01 | not evidence | P2-01 may continue. P2-02 and later packages are not authorized. |

P2-01 model tests are not database, RLS, worker, or Phase 2 exit evidence. See Q83 and Q117.

`PP-P2-DEC-003`, `PP-P2-DEC-022`, and `PP-P2-DEC-023` stay in the decision register. These 120 answers do not restate Innago retirement, the Yarn lockfile, or the prohibition on autonomous protected decisions, so they are not given questionnaire rows.

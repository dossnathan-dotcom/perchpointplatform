# Phase 8 approved customization answers

Nathan Doss approved Q1-Q120 for local Phase 8 implementation. These answers do not grant hosted, stakeholder, legal, real-data, or production acceptance.

| Q1 | Complete Phase 8A through 8F only, and keep discovery, CRM, showing, application, lease, finance, and maintenance behavior in later phases. |
| Q2 | Establish one governed source of property and listing truth across every authorized HawkVision and PerchPoint surface. |
| Q3 | Support residential, commercial, mixed-use, single-family, duplex, triplex, multifamily, storage, and parking in one canonical model. |
| Q4 | Evolve the accepted property slice in place and preserve identifiers, contracts, row security, audit, and existing behavior. |
| Q5 | Canonical Phase 8 facts and approved snapshots override CMS presentation whenever they describe property truth. |
| Q6 | Use synthetic data and provider-neutral boundaries, with no production provider or real-data activation. |
| Q7 | Optimize administration for the operations manager, then bounded staff reads and owner exception review. |
| Q8 | Use exception-based, policy-driven owner involvement and keep routine coordination off the owner. |
| Q9 | Measure completeness, freshness, accuracy, edit conflicts, media performance, propagation, and leakage. |
| Q10 | Preserve safe reads and drafts during dependency failure, and block unsafe writes with server-controlled idempotent queues. |
| Q11 | Preserve organization-scoped property, building, and space containment, and retain legal-owner, management, portfolio, and grouping relationships. |
| Q12 | Represent a single-family home through an explicit primary building and residential space behind a simple home-oriented screen. |
| Q13 | Keep the canonical space record and use contextual Home, Unit, Suite, or Space labels only in the interface. |
| Q14 | Use immutable identifiers, human-readable references, and stable public slugs, and never treat a provider identifier as authority. |
| Q15 | Store structured addresses with the original input, normalization provenance, and an explicit manual override. |
| Q16 | Support one primary property location plus governed building-level addresses for multi-address and mixed-use sites. |
| Q17 | Use a versioned controlled property-type taxonomy with stable codes and explicit migration rules. |
| Q18 | Use governed space types with capability flags and validated residential or commercial subtype fields. |
| Q19 | Use typed nullable measurements with units, precision, provenance, and type-specific validation. |
| Q20 | Allow governed typed custom fields only for noncore facts, and do not turn core data into unrestricted JSON. |
| Q21 | Keep lifecycle, physical readiness, occupancy, marketing availability, restrictions, and publication as separate dimensions. |
| Q22 | Support not-assessed, occupied-not-turning, notice-pending, turn-required, work-in-progress, inspection-required, ready, and blocked readiness, reconciled with accepted lifecycle states. |
| Q23 | Support not-offered, coming-soon, available, temporary-hold, application-pending, lease-pending, leased, and off-market availability with guarded transitions. |
| Q24 | Derive occupancy from authoritative agreement relationships, and allow only a narrow audited correction rather than a casual occupied checkbox. |
| Q25 | Store the availability effective date, exact or estimated confidence, source, last confirmation, and reason. |
| Q26 | Support time-bounded holds with reason, owner, expiry, release, and audit, and do not treat a hold as a housing decision. |
| Q27 | Use freshness timestamps, review intervals, warnings, an exception queue, and a safe stale-unpublication policy. |
| Q28 | Withdraw availability by atomically updating truth, audit, the outbox, cache, and the public projection. |
| Q29 | Restore an archived record through a validated new active version while preserving history. |
| Q30 | Execute transitions on the server, transactionally, with a version check, idempotency, and an audit record. |
| Q31 | Use immutable effective-dated asking-price versions with currency, period, dates, reason, actor, approval, and publication state. |
| Q32 | Use monthly as the residential default and a governed extensible billing-period model for legitimate commercial cases. |
| Q33 | Model deposits as separate effective-dated components with formula or amount, refundability, conditions, legal-review state, and label. |
| Q34 | Itemize fees by required or optional, recurring or one-time, refundable or not, applicability, amount or formula, and effective date. |
| Q35 | Structure each utility as included, tenant-paid, allocated, metered, or not yet classified, together with an approved explanation. |
| Q36 | Show an itemized estimated move-in amount only when the applicable components are complete, with assumptions and a non-ledger disclaimer. |
| Q37 | Store approved listing-level billing-policy facts only, because later ledger phases own calculations, allocation, statements, and postings. |
| Q38 | Structure pet policy and charges, and keep assistance animals outside ordinary pet-fee logic pending qualified review. |
| Q39 | Treat concessions as time-bounded approved versions with eligibility, clear terms, and expiry, and never rewrite base rent silently. |
| Q40 | Permit routine policy-bounded manager price changes, and require Faruk for material deviations, new fee policy, or reserved decisions. |
| Q41 | Use inherited property and building defaults with explicit space overrides and visible provenance. |
| Q42 | Manage amenities through a governed taxonomy with scope, category, public label, icon token, state, and verified details. |
| Q43 | Permit reviewed custom amenity facts while keeping the core filters on the controlled taxonomy. |
| Q44 | Publish specific verified physical accessibility facts without guaranteeing legal accessibility or suitability. |
| Q45 | Structure pet rules, limits, approvals, and charges, with assistance-animal treatment kept separate. |
| Q46 | Structure smoking policies by scope and effective date, using approved wording. |
| Q47 | Model parking type, count, assignment facts, accessibility, price, and restrictions without implementing allocation or payment. |
| Q48 | Publish approved offered term ranges and notes, and leave final lease terms to the later lease phase. |
| Q49 | Version descriptions with author, review, fair-housing checks, and canonical fact linkage, and do not publish them autonomously. |
| Q50 | Publish an approved exact address only for an actively marketed record; otherwise project a safe locality and never publish access instructions. |
| Q51 | Phase 8 owns property, building, and space listing images, floor plans, approved documents, and allowlisted tour references, while general brand media stays with the content phase. |
| Q52 | Use immutable asset identity, versioned metadata, and explicit reusable associations rather than copied bytes or raw public URLs. |
| Q53 | Require server-authorized limits, signature and media-type verification, malware scan, safe decode, metadata stripping, quarantine, and controlled promotion. |
| Q54 | Generate deterministic responsive dimensions, formats, and fallbacks with hashes, quality budgets, and idempotent regeneration. |
| Q55 | Use versioned ordered associations and exactly one valid primary asset for each applicable publication scope. |
| Q56 | Require alt text or a decorative state, a useful caption, category, orientation, rights, review state, and verification metadata. |
| Q57 | Require source, uploader, ownership or license basis, date when known, usage scope, and revocation status before publication. |
| Q58 | Use human publication review, supported by warnings for people, documents, plates, codes, keys, belongings, and unsafe metadata. |
| Q59 | Permit only allowlisted tour providers or internal references, with a content-security-safe embed and an accessible fallback. |
| Q60 | Replace media through new assets and retired associations while preserving historical snapshot bytes and audit. |
| Q61 | Public listing reads consume immutable approved snapshots derived from canonical Phase 8 records. |
| Q62 | Snapshot the allowlisted facts, media, price, fees, utilities, availability, and policies with provenance, schema version, and a content hash. |
| Q63 | Require complete facts, valid fresh availability, approved pricing and policies, safe media, authority, and payload validation before publication. |
| Q64 | Preview is authorized, expiring, noindex, no-store, audited, and visibly nonpublic. |
| Q65 | Scheduled publication and unpublication use idempotent jobs and recheck authority, version, validity, and freshness at execution. |
| Q66 | Emergency unpublication is immediate, reasoned, audited, evented, cache-purged, and history-preserving. |
| Q67 | Use transactional outbox invalidation, versioned cache keys, idempotent purge and rebuild, monitoring, and drift repair. |
| Q68 | Reuse stable slugs and redirects, prevent collisions, and do not regenerate a URL because the price or title changed. |
| Q69 | Project one property with attributable publishable space options, and do not duplicate property truth or implement discovery. |
| Q70 | Emit versioned events for structure, readiness, availability, pricing, media lifecycle, publication, archive, restore, and staleness. |
| Q71 | Define action and scope permissions on the accepted roles, property scope, conditions, and row security, and do not treat interface visibility as authority. |
| Q72 | The operations-manager role may perform routine scoped administration inside the configured policy. |
| Q73 | Faruk retains material pricing and fee policy, portfolio-wide commitments, designated strategic publication, and reserved disposition decisions. |
| Q74 | Determine pricing materiality with configured absolute and percentage bands, floors, ceilings, approved ranges, dates, and reasons, not the procurement threshold. |
| Q75 | Authorized operations and leasing staff may publish a complete routine listing, while an exception-bearing snapshot requires designated approval. |
| Q76 | Authorized editors may retire media, and destructive deletion requires retention checks plus elevated authority. |
| Q77 | Archive requires elevated scope, dependency and impact checks, a reason, confirmation, and owner approval where the decision is reserved. |
| Q78 | Reuse scoped, expiring, auditable delegation, and keep owner-reserved decisions from being delegated. |
| Q79 | Background work uses least-privilege service principals, explicit scopes, idempotency, and audit. |
| Q80 | Audit the actor, effective actor, delegation, scope, versions, reason, approval, correlation, source, event lineage, and sensitive reads or exports. |
| Q81 | Deliver a searchable portfolio workspace, governed views, a property workspace, completeness indicators, and exception queues. |
| Q82 | Filter by type, location, readiness, availability, occupancy, publication, freshness, missing facts, media, price state, holds, and exceptions. |
| Q83 | Use sectioned typed forms, a dirty-state warning, permission-aware controls, completeness guidance, and a high-impact review summary. |
| Q84 | Use optimistic concurrency, versions, conflict responses, field-aware diffs, and an explicit refresh or merge. |
| Q85 | Autosave only clearly labeled low-risk drafts, and require an explicit confirmed save or publish for canonical high-impact changes. |
| Q86 | Bulk work requires selection, allowlisted fields, a dry run, validation, an impact summary, an execution recheck, per-record results, audit, and compensation. |
| Q87 | Duplication copies only approved structural template facts into a new draft with new identifiers, and never copies residents, leases, applications, access, history, holds, publication, or unverified rights. |
| Q88 | Archive by default, and allow hard deletion only for an unreferenced erroneous draft under retention policy and elevated authority. |
| Q89 | Rollback creates a new validated version from selected prior facts and never rewrites history. |
| Q90 | Administration meets WCAG 2.2 AA and stays usable by keyboard, assistive technology, zoom, reflow, reduced motion, tablet, and urgent mobile actions. |
| Q91 | Public pages consume authorized approved-snapshot projections and never read private administration tables directly. |
| Q92 | The content system owns editorial presentation, while Phase 8 owns property facts, media associations, pricing, policies, and availability through explicit contracts. |
| Q93 | Prepare stable snapshots, eligibility signals, events, and adapter-ready contracts for a later discovery phase without building syndication. |
| Q94 | Provide stable listing and snapshot references and availability facts for a later inquiry phase without building CRM behavior. |
| Q95 | Provide readiness and availability capabilities and references for later showing, application, and lease phases without their workflows. |
| Q96 | Future imports use staging, mapping, validation, idempotency, provenance, conflict reports, dry runs, crosswalks, and PerchPoint identifiers. |
| Q97 | Implement authorized administrative inventory search, and leave full public discovery, relevance, and saved search for a later phase. |
| Q98 | Use indexed server pagination, bounded projections, batched media metadata, asynchronous processing, event caches, and query-plan review. |
| Q99 | Prove a representative scale of about 1001 properties, 3000 spaces, 25000 operational rows, and 250000 audit or event rows, with concurrency. |
| Q100 | Provide structured logs, metrics, correlation, queue and media and staleness and cache-drift visibility, retry and dead-letter visibility, replay, alerts, and runbooks. |
| Q101 | Enforce forced row security plus server authorization, organization and property scope, allowlisted projections, and direct denial tests for API, storage, search, and export. |
| Q102 | Classify fields as public-approved, internal operational, confidential, restricted, or prohibited from the public projection, with explicit treatment. |
| Q103 | Protect public payloads through schema allowlists, snapshot validation, serializer tests, cache isolation, and prohibited-field regressions. |
| Q104 | Never publish resident, applicant, lease, or account data, internal cost, access details, notes, vendor data, private documents, or unapproved contacts. |
| Q105 | Use governed wording rules, prohibited-language checks, factual templates, human review, audit, and qualified production review for fair-housing risk. |
| Q106 | Version legal-review status, jurisdiction, effective date, reviewer, and unresolved questions for fees, deposits, policies, and claims, and block production where required. |
| Q107 | Apply publication-state address rules, exclude access instructions, review sensitive media, restrict internal fields, and audit elevated access. |
| Q108 | Test malware, polyglot files, decompression bombs, metadata leakage, script content, enumeration, signed-address abuse, cache poisoning, unsafe embeds, and resource exhaustion. |
| Q109 | Prove Chromium, Firefox, and WebKit, keyboard use, automated accessibility, responsive widths 320, 768, 1024, and 1440, focus, contrast, zoom, errors, and reduced motion. |
| Q110 | Reuse class-based retention and legal hold for drafts, versions, snapshots, originals, derivatives, imports, audits, and retired records. |
| Q111 | Reconcile the baseline and freeze decisions, contracts, states, permissions, and projections before substantial interface work. |
| Q112 | Cursor owns architecture, data, security, tests, reconciliation, and final local authority, and an external design lane cannot block local completion. |
| Q113 | Use governed synthetic scenarios covering property types, states, histories, media failures, conflicts, and unauthorized actors. |
| Q114 | Require governance, contract, migration, constraint, state, authorization, leakage, pricing, availability, media, publication, bulk, concurrency, event, browser, accessibility, performance, recovery, and regression tests. |
| Q115 | Retain clean-room proof for build, migrations, seed, administration, media, pricing, availability, publication, public projection, recovery, browsers, security, performance, and teardown. |
| Q116 | Measure representative median, 95th percentile, and maximum latency, errors, timeouts, plans, media throughput, cache freshness, bulk performance, and inherited regressions. |
| Q117 | Perform independent product, architecture, database, authorization, privacy, media, fair-housing-boundary, accessibility, performance, operations, recovery, and phase-boundary review, then remediate. |
| Q118 | Use governed behavior and evidence binding, one focused pull request, exact-head checks, a protected merge, and merged-main verification, with no direct evidence push to main. |
| Q119 | Phase 8 may grant local technical acceptance only, while hosted, stakeholder, legal, real-data, provider, and production verdicts remain separate. |
| Q120 | The definition of done is the tested, audited, accessible, performant, secure, and evidenced Phase 8 workflow, with every local gate green and later phases untouched. |

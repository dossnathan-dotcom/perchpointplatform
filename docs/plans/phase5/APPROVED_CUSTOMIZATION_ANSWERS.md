# Phase 5 approved customization answers

Nathan Doss approved Q1–Q160, including the Supabase clarification in the Phase 5 directive.

| Question | Approved answer |
| --- | --- |
| Q1 | Build a production-grade canonical information layer for records, provenance, documents, search, audit, and events. |
| Q2 | Do not activate new leasing, payment, maintenance, or accounting workflows. Support their future data needs only. |
| Q3 | Progressively replace equivalent Phase 0 fixtures with PostgreSQL-backed records without breaking accepted preview routes. |
| Q4 | Preserve and extend the modular monolith. Do not introduce microservices. |
| Q5 | Use local PostgreSQL for development, CI, benchmarks, clean-room recovery, and deterministic evidence. |
| Q6 | Designate Supabase as hosted staging and eventual production data and storage. Do not require production activation in Phase 5. |
| Q7 | Use one S3-compatible application abstraction: local object storage now, Supabase Storage when hosted. |
| Q8 | Keep provider configuration environment-isolated. Production remains deferred. |
| Q9 | Require no production secrets. Local synthetic credentials stay outside Git. |
| Q10 | Repair Phase 5 baseline defects, including the audit_events permission warning, without weakening audit immutability. |
| Q11 | Canonical records require stable UUIDs, organization ownership, provenance, lifecycle, timestamps, version, and validated relationships. |
| Q12 | Provider identifiers are references, never PerchPoint primary keys. |
| Q13 | Preserve property, building, and space containment, including mixed use. |
| Q14 | Model ownership, management, occupancy, and portfolio membership as effective-dated relationships. |
| Q15 | Permit multiple buildings per property. |
| Q16 | Permit residential and commercial spaces in the same building. |
| Q17 | Represent parking, storage, common, mechanical, and other non-leasable spaces explicitly. |
| Q18 | Support vacant land and development property without fake buildings or units. |
| Q19 | End-date historical relationships rather than overwriting them. |
| Q20 | Enforce non-overlap only for exclusive relationships. |
| Q21 | Store structured address components, untouched source text, and optional geocoding metadata. |
| Q22 | Do not call a live geocoder in Phase 5. Keep an adapter boundary and synthetic coordinates only when supplied. |
| Q23 | Support jurisdiction-scoped parcel identifiers with provenance. |
| Q24 | Permit multiple parcels per property. |
| Q25 | Normalize construction, area, beds, baths, floors, accessibility, utilities, parking, zoning, occupancy, and condition facts. |
| Q26 | Imported and inferred facts keep confidence and provenance. Verified facts keep verifier and verification date. |
| Q27 | Keep core searchable facts in columns. Use versioned extensions only for justified variability. |
| Q28 | Model commercial-use facts separately from residential facts on the shared space core. |
| Q29 | Represent current property issues without activating the maintenance workflow. |
| Q30 | Support expiration for inspections, insurance, permits, certifications, and compliance facts. |
| Q31 | Support person, household, legal entity, vendor, employer, government, and internal organization parties. |
| Q32 | Household is a canonical record. The default remains one primary portal account. |
| Q33 | Additional adults may authenticate individually. Shared passwords are not required. |
| Q34 | Household membership is effective-dated. |
| Q35 | One person may hold multiple roles without duplicate person records. |
| Q36 | Authentication identity stays separate from person and business-party identity. |
| Q37 | Contact points are separate and carry verification, preference, consent, source, and validity. |
| Q38 | Store preferred language and communication channel for future workflows. |
| Q39 | Store only minimum safe screening and payment-provider references. |
| Q40 | Never auto-merge suspected duplicates. Create attributable reviewed merge proposals. |
| Q41 | Imported records identify source system, batch, original identifier, time, and transformation version. |
| Q42 | Manual records identify actor, interface, and request. |
| Q43 | Preserve raw imported values separately from normalized values. |
| Q44 | Use confidence only for inferred mappings. Do not label invalid data authoritative. |
| Q45 | Classify findings as blocker, review-required warning, or information. |
| Q46 | Quarantine questionable imports instead of writing them directly to canonical tables. |
| Q47 | Version data-quality rules and record the version that produced each finding. |
| Q48 | Findings require an attributable resolution and cannot be silently dismissed. |
| Q49 | Data-quality results expose component measurements and are not opaque scores. |
| Q50 | Faruk receives material data-risk exceptions, not ordinary cleanup noise. |
| Q51 | Keep condition, occupancy, availability, publication, restriction, and legal state as separate dimensions. |
| Q52 | Protected transitions use authorized commands with reason, expected version, idempotency, audit, and events. |
| Q53 | Clients cannot directly patch protected state fields. |
| Q54 | Permitted transitions are explicit. |
| Q55 | Scheduled effective dates stay distinct from completed changes. |
| Q56 | Backdating is limited to authorized corrections and imports with reason and audit. |
| Q57 | Ordinary interfaces do not hard-delete canonical records. |
| Q58 | Optimistic concurrency returns a safe conflict when the version is stale. |
| Q59 | A mutation, its audit, its outbox event, and its command result commit together. |
| Q60 | Unavailable transitions explain the missing prerequisite to an authorized user. |
| Q61 | Audit creates, material changes, transitions, relationships, restricted document access, exports, permission decisions, merges, and deletions. |
| Q62 | Capture principal, role, organization, request, and interface on audited actions. |
| Q63 | Store structured redacted before-and-after evidence. |
| Q64 | Never copy secrets or protected values into audit payloads. |
| Q65 | Runtime roles cannot update or delete audit entries. |
| Q66 | Audit material denied and failed actions. |
| Q67 | Audit sensitive reads without recording ordinary harmless reads. |
| Q68 | Add tamper-evident digests. Do not add a blockchain. |
| Q69 | Filter audit history by actor, resource, action, property, date, request, severity, and organization. |
| Q70 | The owner audit view emphasizes anomalies, overdue decisions, material changes, and unresolved conflicts. |
| Q71 | Domain events stay distinct from audit evidence. |
| Q72 | Event envelopes carry identity, type, schema version, times, actor, organization, aggregate, correlation, causation, and a redacted payload. |
| Q73 | Version event schemas and keep changes additive. |
| Q74 | Extend the PostgreSQL outbox and worker. Do not add Kafka or a workflow engine. |
| Q75 | Claim at-least-once delivery with idempotent consumers. |
| Q76 | Keep a durable inbox for future external events without activating providers. |
| Q77 | Timelines are projections from events, audits, documents, and authorized notes. |
| Q78 | Corrections append evidence and do not erase history. |
| Q79 | Timeline evidence links are checked again at read time. |
| Q80 | Administrators can inspect retries and dead letters. Other users see safe outcomes. |
| Q81 | Search properties, buildings, spaces, parties, relationships, inquiries, documents, identifiers, and authorized timeline metadata. |
| Q82 | Use PostgreSQL full text and trigram indexes. Do not add an external search engine. |
| Q83 | Do not add vector or semantic search in Phase 5. |
| Q84 | Search uses the same row-level security and authorization as direct reads. |
| Q85 | Do not leak unauthorized existence through results, counts, suggestions, facets, snippets, or exports. |
| Q86 | Rank exact identifiers, then exact names and addresses, then prefixes, then other text. |
| Q87 | Use conservative fuzzy matching. |
| Q88 | Support quoted phrases and structured filters. |
| Q89 | Filter by record type, property scope, status, document class, date, source, and quality state. |
| Q90 | Explain matches with permission-safe fields. Restricted titles are not shown. |
| Q91 | Activate authenticated global search and the command palette. |
| Q92 | Keep public search limited to published listing data. |
| Q93 | Support keyboard-first search with a status announcement. |
| Q94 | Start typeahead after two characters, wait about 200 milliseconds, and cancel stale requests. |
| Q95 | Store recent searches as query text only. |
| Q96 | Allow private saved searches for internal roles. |
| Q97 | Shared searches are evaluated again under the current viewer. |
| Q98 | Indexing changes are durable and replayable. |
| Q99 | Accepted changes are searchable as part of the same committed write. |
| Q100 | Measure common internal search latency against the synthetic scale and record the result. |
| Q101 | Support property, ownership, leasing, applicant, resident, maintenance, vendor, financial-operational, compliance, insurance, legal, and administration document classes. |
| Q102 | Use a controlled document class recorded on each document. |
| Q103 | Only platform administration changes the type registry. Staff apply classes already allowed. |
| Q104 | Require one primary resource association. |
| Q105 | Additional relationships may be added later without replacing the primary context. |
| Q106 | Require title, class, classification, primary resource, source, and lifecycle. |
| Q107 | Support independent expiration dates on facts and policies. |
| Q108 | Prefer controlled classes over free-form folders. |
| Q109 | Classify content as public, internal, confidential, or restricted. |
| Q110 | Do not derive authorization from a folder path. |
| Q111 | Keep document metadata in PostgreSQL. |
| Q112 | Store bytes through the S3-compatible abstraction. |
| Q113 | Do not store ordinary file bytes in PostgreSQL. |
| Q114 | Object keys are organization-scoped and non-guessable. |
| Q115 | Original filenames are metadata only. |
| Q116 | Replacements add immutable document versions. |
| Q117 | Duplicate detection uses a checksum inside one organization. |
| Q118 | A matching checksum never grants another organization's access. |
| Q119 | The default upload maximum is 50 MB. |
| Q120 | Rejected and unscanned uploads do not become available documents. |
| Q121 | Allow verified PDF, common images, DOCX, XLSX, CSV, and plain text. |
| Q122 | Block executables, scripts, macro-enabled Office files, disk images, and unapproved archives. |
| Q123 | Check signature, declared type, and extension together. |
| Q124 | Scan through a replaceable scanner interface. Use ClamAV when its endpoint is configured. |
| Q125 | Quarantine suspicious files and keep them unavailable. |
| Q126 | Test malware handling with an EICAR payload generated in the test, never committed as a fixture. |
| Q127 | Do not promote extracted metadata over the original bytes. |
| Q128 | Quarantine encrypted or password-protected files. |
| Q129 | Extracted text is a derived artifact and does not replace the original. |
| Q130 | Derived text stays linked to the source version. |
| Q131 | Generate no browser-executed preview for Office files. |
| Q132 | Do not expose permanent object URLs. |
| Q133 | Signed access defaults to a short lifetime when object storage signatures are enabled. |
| Q134 | Do not mark restricted bytes as publicly cacheable. |
| Q135 | Audit restricted document reads. |
| Q136 | A document is public only when its classification is public. |
| Q137 | External roles do not receive a new authentication workflow in Phase 5. |
| Q138 | Bulk destruction and export remain explicit audited commands. |
| Q139 | A denial uses the same not-found response as a missing document. |
| Q140 | Retention policy is configurable and is not Ohio legal advice. |
| Q141 | Retention is based on document class. |
| Q142 | Legal hold overrides disposition. |
| Q143 | Hold placement is an audited command. |
| Q144 | Expiration marks review eligibility and does not delete immediately. |
| Q145 | Restricted destruction requires two matching confirmations. |
| Q146 | Backup copies are not promised to disappear immediately. |
| Q147 | Audit evidence remains after content is withheld. |
| Q148 | Exports must carry authorization and audit before they are added. |
| Q149 | Retention defaults are labeled provisional and cannot be treated as production legal approval. |
| Q150 | Deliver authenticated search, document commands, import staging, and audit protection. |
| Q151 | Keep the Phase 4 design system and progressive disclosure. |
| Q152 | Owner surfaces stay focused on material exceptions. |
| Q153 | Operations can search and prepare imports without receiving developer internals. |
| Q154 | Platform administration can manage the canonical records and diagnostics that Phase 5 implements. |
| Q155 | Stage CSV imports. Do not connect to Innago. |
| Q156 | Imports run as staging, validation, and an explicit apply step. |
| Q157 | Scale evidence is generated in a disposable database and removed afterward. |
| Q158 | Security gates include forced row-level security, cross-organization isolation, malicious-file handling, and audit immutability. |
| Q159 | Phase 5 acceptance requires executed evidence. A planned gate is not a passed gate. |
| Q160 | Phase 6 identity, production deployment, live providers, and real tenant data stay outside Phase 5. |

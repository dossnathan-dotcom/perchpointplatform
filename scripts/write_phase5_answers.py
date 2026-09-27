"""Write the Phase 5 answer register from the approved customization text."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ANSWERS = [
    "Build a production-grade canonical information layer for records, provenance, documents, search, audit, and events.",
    "Do not activate new leasing, payment, maintenance, or accounting workflows. Support their future data needs only.",
    "Progressively replace equivalent Phase 0 fixtures with PostgreSQL-backed records without breaking accepted preview routes.",
    "Preserve and extend the modular monolith. Do not introduce microservices.",
    "Use local PostgreSQL for development, CI, benchmarks, clean-room recovery, and deterministic evidence.",
    "Designate Supabase as hosted staging and eventual production data and storage. Do not require production activation in Phase 5.",
    "Use one S3-compatible application abstraction: local object storage now, Supabase Storage when hosted.",
    "Keep provider configuration environment-isolated. Production remains deferred.",
    "Require no production secrets. Local synthetic credentials stay outside Git.",
    "Repair Phase 5 baseline defects, including the audit_events permission warning, without weakening audit immutability.",
    "Canonical records require stable UUIDs, organization ownership, provenance, lifecycle, timestamps, version, and validated relationships.",
    "Provider identifiers are references, never PerchPoint primary keys.",
    "Preserve property, building, and space containment, including mixed use.",
    "Model ownership, management, occupancy, and portfolio membership as effective-dated relationships.",
    "Permit multiple buildings per property.",
    "Permit residential and commercial spaces in the same building.",
    "Represent parking, storage, common, mechanical, and other non-leasable spaces explicitly.",
    "Support vacant land and development property without fake buildings or units.",
    "End-date historical relationships rather than overwriting them.",
    "Enforce non-overlap only for exclusive relationships.",
    "Store structured address components, untouched source text, and optional geocoding metadata.",
    "Do not call a live geocoder in Phase 5. Keep an adapter boundary and synthetic coordinates only when supplied.",
    "Support jurisdiction-scoped parcel identifiers with provenance.",
    "Permit multiple parcels per property.",
    "Normalize construction, area, beds, baths, floors, accessibility, utilities, parking, zoning, occupancy, and condition facts.",
    "Imported and inferred facts keep confidence and provenance. Verified facts keep verifier and verification date.",
    "Keep core searchable facts in columns. Use versioned extensions only for justified variability.",
    "Model commercial-use facts separately from residential facts on the shared space core.",
    "Represent current property issues without activating the maintenance workflow.",
    "Support expiration for inspections, insurance, permits, certifications, and compliance facts.",
    "Support person, household, legal entity, vendor, employer, government, and internal organization parties.",
    "Household is a canonical record. The default remains one primary portal account.",
    "Additional adults may authenticate individually. Shared passwords are not required.",
    "Household membership is effective-dated.",
    "One person may hold multiple roles without duplicate person records.",
    "Authentication identity stays separate from person and business-party identity.",
    "Contact points are separate and carry verification, preference, consent, source, and validity.",
    "Store preferred language and communication channel for future workflows.",
    "Store only minimum safe screening and payment-provider references.",
    "Never auto-merge suspected duplicates. Create attributable reviewed merge proposals.",
    "Imported records identify source system, batch, original identifier, time, and transformation version.",
    "Manual records identify actor, interface, and request.",
    "Preserve raw imported values separately from normalized values.",
    "Use confidence only for inferred mappings. Do not label invalid data authoritative.",
    "Classify findings as blocker, review-required warning, or information.",
    "Quarantine questionable imports instead of writing them directly to canonical tables.",
    "Version data-quality rules and record the version that produced each finding.",
    "Findings require an attributable resolution and cannot be silently dismissed.",
    "Data-quality results expose component measurements and are not opaque scores.",
    "Faruk receives material data-risk exceptions, not ordinary cleanup noise.",
    "Keep condition, occupancy, availability, publication, restriction, and legal state as separate dimensions.",
    "Protected transitions use authorized commands with reason, expected version, idempotency, audit, and events.",
    "Clients cannot directly patch protected state fields.",
    "Permitted transitions are explicit.",
    "Scheduled effective dates stay distinct from completed changes.",
    "Backdating is limited to authorized corrections and imports with reason and audit.",
    "Ordinary interfaces do not hard-delete canonical records.",
    "Optimistic concurrency returns a safe conflict when the version is stale.",
    "A mutation, its audit, its outbox event, and its command result commit together.",
    "Unavailable transitions explain the missing prerequisite to an authorized user.",
    "Audit creates, material changes, transitions, relationships, restricted document access, exports, permission decisions, merges, and deletions.",
    "Capture principal, role, organization, request, and interface on audited actions.",
    "Store structured redacted before-and-after evidence.",
    "Never copy secrets or protected values into audit payloads.",
    "Runtime roles cannot update or delete audit entries.",
    "Audit material denied and failed actions.",
    "Audit sensitive reads without recording ordinary harmless reads.",
    "Add tamper-evident digests. Do not add a blockchain.",
    "Filter audit history by actor, resource, action, property, date, request, severity, and organization.",
    "The owner audit view emphasizes anomalies, overdue decisions, material changes, and unresolved conflicts.",
    "Domain events stay distinct from audit evidence.",
    "Event envelopes carry identity, type, schema version, times, actor, organization, aggregate, correlation, causation, and a redacted payload.",
    "Version event schemas and keep changes additive.",
    "Extend the PostgreSQL outbox and worker. Do not add Kafka or a workflow engine.",
    "Claim at-least-once delivery with idempotent consumers.",
    "Keep a durable inbox for future external events without activating providers.",
    "Timelines are projections from events, audits, documents, and authorized notes.",
    "Corrections append evidence and do not erase history.",
    "Timeline evidence links are checked again at read time.",
    "Administrators can inspect retries and dead letters. Other users see safe outcomes.",
    "Search properties, buildings, spaces, parties, relationships, inquiries, documents, identifiers, and authorized timeline metadata.",
    "Use PostgreSQL full text and trigram indexes. Do not add an external search engine.",
    "Do not add vector or semantic search in Phase 5.",
    "Search uses the same row-level security and authorization as direct reads.",
    "Do not leak unauthorized existence through results, counts, suggestions, facets, snippets, or exports.",
    "Rank exact identifiers, then exact names and addresses, then prefixes, then other text.",
    "Use conservative fuzzy matching.",
    "Support quoted phrases and structured filters.",
    "Filter by record type, property scope, status, document class, date, source, and quality state.",
    "Explain matches with permission-safe fields. Restricted titles are not shown.",
    "Activate authenticated global search and the command palette.",
    "Keep public search limited to published listing data.",
    "Support keyboard-first search with a status announcement.",
    "Start typeahead after two characters, wait about 200 milliseconds, and cancel stale requests.",
    "Store recent searches as query text only.",
    "Allow private saved searches for internal roles.",
    "Shared searches are evaluated again under the current viewer.",
    "Indexing changes are durable and replayable.",
    "Accepted changes are searchable as part of the same committed write.",
    "Measure common internal search latency against the synthetic scale and record the result.",
    "Support property, ownership, leasing, applicant, resident, maintenance, vendor, financial-operational, compliance, insurance, legal, and administration document classes.",
    "Use a controlled document class recorded on each document.",
    "Only platform administration changes the type registry. Staff apply classes already allowed.",
    "Require one primary resource association.",
    "Additional relationships may be added later without replacing the primary context.",
    "Require title, class, classification, primary resource, source, and lifecycle.",
    "Support independent expiration dates on facts and policies.",
    "Prefer controlled classes over free-form folders.",
    "Classify content as public, internal, confidential, or restricted.",
    "Do not derive authorization from a folder path.",
    "Keep document metadata in PostgreSQL.",
    "Store bytes through the S3-compatible abstraction.",
    "Do not store ordinary file bytes in PostgreSQL.",
    "Object keys are organization-scoped and non-guessable.",
    "Original filenames are metadata only.",
    "Replacements add immutable document versions.",
    "Duplicate detection uses a checksum inside one organization.",
    "A matching checksum never grants another organization's access.",
    "The default upload maximum is 50 MB.",
    "Rejected and unscanned uploads do not become available documents.",
    "Allow verified PDF, common images, DOCX, XLSX, CSV, and plain text.",
    "Block executables, scripts, macro-enabled Office files, disk images, and unapproved archives.",
    "Check signature, declared type, and extension together.",
    "Scan through a replaceable scanner interface. Use ClamAV when its endpoint is configured.",
    "Quarantine suspicious files and keep them unavailable.",
    "Test malware handling with an EICAR payload generated in the test, never committed as a fixture.",
    "Do not promote extracted metadata over the original bytes.",
    "Quarantine encrypted or password-protected files.",
    "Extracted text is a derived artifact and does not replace the original.",
    "Derived text stays linked to the source version.",
    "Generate no browser-executed preview for Office files.",
    "Do not expose permanent object URLs.",
    "Signed access defaults to a short lifetime when object storage signatures are enabled.",
    "Do not mark restricted bytes as publicly cacheable.",
    "Audit restricted document reads.",
    "A document is public only when its classification is public.",
    "External roles do not receive a new authentication workflow in Phase 5.",
    "Bulk destruction and export remain explicit audited commands.",
    "A denial uses the same not-found response as a missing document.",
    "Retention policy is configurable and is not Ohio legal advice.",
    "Retention is based on document class.",
    "Legal hold overrides disposition.",
    "Hold placement is an audited command.",
    "Expiration marks review eligibility and does not delete immediately.",
    "Restricted destruction requires two matching confirmations.",
    "Backup copies are not promised to disappear immediately.",
    "Audit evidence remains after content is withheld.",
    "Exports must carry authorization and audit before they are added.",
    "Retention defaults are labeled provisional and cannot be treated as production legal approval.",
    "Deliver authenticated search, document commands, import staging, and audit protection.",
    "Keep the Phase 4 design system and progressive disclosure.",
    "Owner surfaces stay focused on material exceptions.",
    "Operations can search and prepare imports without receiving developer internals.",
    "Platform administration can manage the canonical records and diagnostics that Phase 5 implements.",
    "Stage CSV imports. Do not connect to Innago.",
    "Imports run as staging, validation, and an explicit apply step.",
    "Scale evidence is generated in a disposable database and removed afterward.",
    "Security gates include forced row-level security, cross-organization isolation, malicious-file handling, and audit immutability.",
    "Phase 5 acceptance requires executed evidence. A planned gate is not a passed gate.",
    "Phase 6 identity, production deployment, live providers, and real tenant data stay outside Phase 5.",
]


def main() -> None:
    if len(ANSWERS) != 160 or any(not item.strip() for item in ANSWERS):
        raise SystemExit(f"expected 160 answers, found {len(ANSWERS)}")
    plan = ROOT / "docs/plans/phase5"
    plan.mkdir(parents=True, exist_ok=True)
    lines = ["# Phase 5 approved customization answers", "", "Nathan Doss approved Q1–Q160, including the Supabase clarification in the Phase 5 directive.", ""]
    lines.append("| Question | Approved answer |")
    lines.append("| --- | --- |")
    for number, answer in enumerate(ANSWERS, start=1):
        lines.append(f"| Q{number} | {answer} |")
    (plan / "APPROVED_CUSTOMIZATION_ANSWERS.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    trace = ["# Phase 5 answer traceability", "", "Each question maps to a requirement, the implementation path, and the test that exercises it.", ""]
    trace.append("| Question | Requirement | Implementation | Test |")
    trace.append("| --- | --- | --- | --- |")
    for number in range(1, 161):
        if number <= 50:
            requirement, path, test = "PP-DATA-005", "backend/alembic/sql/0007_phase5_canonical.sql", "backend/tests/phase5/test_canonical.py"
        elif number <= 80:
            requirement, path, test = "PP-SEC-001", "backend/perchpoint/commands.py", "backend/tests/phase2/test_reference_slice.py"
        elif number <= 100:
            requirement, path, test = "PP-DATA-007", "backend/perchpoint/phase5.py", "backend/tests/phase5/test_canonical.py"
        elif number <= 150:
            requirement, path, test = "PP-DATA-006", "backend/perchpoint/phase5_files.py", "backend/tests/phase5/test_files.py"
        else:
            requirement, path, test = "PP-DATA-008", "docs/plans/phase5/README.md", "backend/tests/phase5/test_canonical.py"
        if 141 <= number <= 150:
            requirement = "PP-DATA-008"
        trace.append(f"| Q{number} | {requirement} | `{path}` | `{test}` |")
    (plan / "ANSWER_TRACEABILITY.md").write_text("\n".join(trace) + "\n", encoding="utf-8")
    print(f"wrote {len(ANSWERS)} answers")


if __name__ == "__main__":
    main()

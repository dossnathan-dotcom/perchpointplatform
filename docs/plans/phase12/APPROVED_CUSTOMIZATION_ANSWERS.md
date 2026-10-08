# Phase 12 approved customization answers

Nathan Doss approved every recommended answer. These sentences are the repository record.

| Q1 | Implemented. Phase 12 completes roadmap items 12A through 12F and defers screening, decisions, adverse action, leases, payments, and production. |
| Q2 | Implemented. A household submits one complete traceable application, and a later correction is a supplement rather than a rewrite. |
| Q3 | Implemented. PerchPoint canonical records and immutable submission snapshots are authoritative, while providers stay subordinate. |
| Q4 | Implemented. An application begins from a server-validated inquiry, prospect, or listing-interest handoff and does not copy mutable CRM text. |
| Q5 | Implemented. Showing history and apply-interest are context only and are never treated as eligibility evidence. |
| Q6 | Implemented. A prospect may start through a server-issued capability, and authorized staff may start through the CRM, under the same rules. |
| Q7 | Enforced invariant. Production screening, identity, e-sign, payment, email, SMS, and storage providers stay inactive, with deterministic local fakes only. |
| Q8 | Implemented. The first staff workflow is applicant completion plus the leasing missing-item and review queue. |
| Q9 | Enforced invariant. The owner is involved only for material policy and systemic exceptions, while routine review stays delegated. |
| Q10 | Implemented. Success is measured by completion integrity, applicant control, timeliness, minimization, document safety, review quality, accessibility, privacy, and isolation. |
| Q11 | Implemented. A dependency outage preserves drafts, shows a truthful degraded state, and never claims upload or notification success without proof. |
| Q12 | External acceptance gate. Phase 12 grants local technical acceptance only, and hosted, stakeholder, legal, real-data, provider, and production verdicts stay separate. |
| Q13 | Implemented. An ordinary application targets one server-resolved eligible listing snapshot, and a general application cannot invent property context. |
| Q14 | Enforced invariant. One application targets one listing and space, and reuse on another listing requires a new application and new disclosures. |
| Q15 | Implemented. A secure capability can start intake, and sensitive continuation requires a verified account. |
| Q16 | Implemented. A draft resumes through a server-held session or an expiring revocable capability with destination verification. |
| Q17 | Implemented. A canonical draft is created only after minimum context and the processing disclosure are accepted. |
| Q18 | Implemented. Autosave writes a bounded section with optimistic concurrency and never shows a saved state that the server did not confirm. |
| Q19 | Implemented. Interrupted uploads and forms resume from server state, checksums, expiry, and an explicit retry. |
| Q20 | Implemented. Inactive drafts use a synthetic 30-day active period, with warning, archive, and legal-hold exceptions. |
| Q21 | Implemented. Staff may assist a draft only in an attributed assisted-entry mode, without impersonation. |
| Q22 | Implemented. A device or session change requires reauthentication or a verified capability exchange. |
| Q23 | Implemented. Applicants see only safe states such as draft, submitted, withdrawn, needs applicant action, and supplemental update received. |
| Q24 | Implemented. A repeated start for the same organization, listing, and household resumes the open application and never merges people silently. |
| Q25 | Implemented. A stale draft edit returns a conflict and keeps the current version instead of last-write-wins. |
| Q26 | Implemented. The primary applicant is a role on one application linked to a Phase 10 prospect, not a new global identity. |
| Q27 | Implemented. Verified name and contact may be reused only after applicant confirmation and an application-specific snapshot. |
| Q28 | Implemented. Legal name and preferred name are stored separately, with purpose, access, correction, and provenance controls. |
| Q29 | Enforced invariant. Prior names are not collected unless a later qualified lawful requirement enables that field. |
| Q30 | Implemented. At least one usable contact route is required, with an accessible staff alternative. |
| Q31 | Implemented. Address history is limited to the approved period and allows a no-fixed-address response. |
| Q32 | Enforced invariant. Government identifiers and SSN stay disabled in Phase 12. |
| Q33 | Explicitly deferred to Phase 13. If a sensitive identifier is later enabled, it must be tokenized or encrypted, masked, and excluded from logs and search. |
| Q34 | Enforced invariant. Date of birth is not collected for application access and is not used to rank an applicant. |
| Q35 | Implemented. Identity state is separate from housing eligibility, and local verification uses a deterministic fake. |
| Q36 | Implemented. An identity or contact correction is versioned, confirmed by the applicant, and keeps immutable history. |
| Q37 | Enforced invariant. Staff cannot silently rewrite an applicant statement and must use a reasoned correction workflow. |
| Q38 | Explicitly deferred to a qualified exception. A deceased, incapacitated, or unavailable participant is not handled by an ordinary staff override. |
| Q39 | Implemented. An application household is scoped to one housing intent and is distinct from a future resident household. |
| Q40 | Implemented. Participant roles are primary, co-applicant, adult occupant, minor occupant, guarantor, and representative. |
| Q41 | Enforced invariant. An adult occupant is modeled separately from a co-applicant and is not assumed to be the same responsibility. |
| Q42 | Implemented. A minor record keeps only minimum occupancy facts and is never invited to consent or sign. |
| Q43 | Implemented. A guarantor is an explicit role with a separate invitation, disclosure, and document scope. |
| Q44 | Implemented. One person may join multiple applications with separate roles, snapshots, and authorization. |
| Q45 | Enforced invariant. Household relationships are not inferred, and family status is not derived from composition. |
| Q46 | Enforced invariant. Household size is used only for lawful occupancy capacity and not for familial-status discrimination. |
| Q47 | Implemented. Adding an adult participant creates a role holder and a scoped expiring invitation. |
| Q48 | Enforced invariant. The primary applicant cannot read another adult's private answers or documents. |
| Q49 | Implemented. Removing a participant before submission revokes the invitation, recalculates completeness, and keeps an audit event. |
| Q50 | Implemented. A participant change after submission is a supplemental household request and does not rewrite the submitted household. |
| Q51 | Enforced invariant. Duplicate participants are detected within one application by contact or identity, never by name alone. |
| Q52 | Enforced invariant. Conflicting roles are rejected by a versioned compatibility rule. |
| Q53 | Enforced invariant. Only the primary applicant or an authorized representative may submit, and only after required adults attest. |
| Q54 | Implemented. A household split or merge creates an explicit new application with consented reuse. |
| Q55 | Implemented. Application context freezes listing identity, snapshot, rent, fees, deposit disclosure, availability, policy version, and deadline. |
| Q56 | Implemented. A material price, fee, or availability change during a draft requires acknowledgement of the new version. |
| Q57 | Implemented. A withdrawn listing stops submission, preserves the draft, and does not auto-transfer the application. |
| Q58 | Implemented. A listing change after submission preserves the submitted snapshot and raises a staff-visible exception. |
| Q59 | Enforced invariant. Fee policy, waiver, and amount may be modeled, but production payment collection stays inactive. |
| Q60 | Enforced invariant. A fee waiver is a governed request and is never a hidden preference signal. |
| Q61 | Implemented. Reuse for another listing is an applicant-controlled copy with new consent and explicit document choices. |
| Q62 | Implemented. Reusable facts carry a visible source date and require re-attestation when freshness expires. |
| Q63 | Implemented. Residential and commercial applications share a foundation and use type-specific fields, documents, and completeness. |
| Q64 | Implemented. Staff may change the target listing only through an applicant-approved copy that preserves the original. |
| Q65 | Implemented. Fields are governed by a versioned schema with purpose, requirement, jurisdiction, role, data class, and effective dates. |
| Q66 | External acceptance gate. Production field approval belongs to Faruk Atmaca plus qualified legal, fair-housing, and privacy review. |
| Q67 | Implemented. Required and optional fields are labeled with why they are needed, who sees them, and whether they block submission. |
| Q68 | Implemented. Income is collected only as approved categories and periods, with no scoring. |
| Q69 | Implemented. Nontraditional income uses neutral source categories and no source-based penalty. |
| Q70 | Implemented. Employment history allows unemployed, self-employed, student, retired, and other truthful paths. |
| Q71 | Implemented. Rental history allows a first-time renter and a no-fixed-history exception. |
| Q72 | Enforced invariant. Reasons for leaving prior housing are not asked unless a later qualified review enables a bounded question. |
| Q73 | Implemented. References are limited to an approved type, contact, relationship, and permission. |
| Q74 | Implemented. Vehicle facts are limited to parking operations and are omitted when the listing does not need them. |
| Q75 | Implemented. Ordinary pet facts stay separate from an assistance-animal request. |
| Q76 | Enforced invariant. Property-use questions stay objective and do not ask health or protected-status questions. |
| Q77 | Enforced invariant. Criminal-history questions stay disabled. |
| Q78 | Enforced invariant. Credit and bankruptcy questions stay disabled, and a self-reported score is rejected. |
| Q79 | Enforced invariant. Eviction-history questions stay disabled. |
| Q80 | Implemented. A commercial application collects entity name, jurisdiction, authorized contacts, intended use, and approved document classes. |
| Q81 | Implemented. Free text is bounded, sanitized, warned against sensitive content, and excluded from unrestricted analytics. |
| Q82 | Implemented. Disclosures are versioned immutable content with jurisdiction, audience, language, and required acknowledgement. |
| Q83 | Enforced invariant. Application processing, documents, screening handoff, references, marketing, and electronic records are separate consent purposes. |
| Q84 | Implemented. Final attestation is tied to the participant, disclosure version, timestamp, and submission snapshot. |
| Q85 | Enforced invariant. Phase 12 is not an electronic-signature platform, and lease signatures remain in Phase 14. |
| Q86 | Implemented. A material disclosure update on a draft requires notice and re-acknowledgement before submission. |
| Q87 | Implemented. A submitted disclosure version is preserved, and a newly required disclosure is a supplemental acknowledgement. |
| Q88 | Implemented. Consent withdrawal is purpose-specific, stops future optional processing, and preserves the lawful record. |
| Q89 | Implemented. Each reviewed translation maps to the same disclosure semantic version and keeps translator provenance. |
| Q90 | Implemented. An applicant can download the accepted disclosure copy with its checksum and without another participant's data. |
| Q91 | Implemented. Presentation evidence records version, locale, artifact reference, and timestamps without invasive tracking. |
| Q92 | Enforced invariant. Marketing consent is never bundled with required application processing. |
| Q93 | Explicitly deferred to a qualified exception. Representative authority requires scoped evidence, review, expiry, and audit. |
| Q94 | External acceptance gate. Production disclosure policy changes require owner approval and a qualified professional review. |
| Q95 | Implemented. Only policy-approved document classes such as income, rental, and commercial evidence may be collected. |
| Q96 | Implemented. Document requirements are versioned by purpose, role, alternatives, size, type, freshness, and completeness effect. |
| Q97 | Enforced invariant. Uploads must match an allowlisted magic value, MIME, and extension, within the size limit. |
| Q98 | Implemented. An upload uses a server-authorized scoped intent, an opaque object key, a checksum, and a finalization command. |
| Q99 | Enforced invariant. A document is usable only after finalization, checksum, type checks, a clean scan, and authorization linkage. |
| Q100 | Implemented. Scanning is quarantine-first, and preview or download is refused before a clean result. |
| Q101 | Implemented. Malicious or unsupported files are rejected with a nondisclosing reason and may be replaced. |
| Q102 | Implemented. Each document records application, participant, class, sensitivity, source, owner, version, and retention metadata. |
| Q103 | Enforced invariant. One participant cannot view another participant's private documents. |
| Q104 | Implemented. Staff preview is permissioned, audited, and short-lived, with no public URL. |
| Q105 | Enforced invariant. Thumbnail and text extraction stay disabled as decision automation and may run only in a sandboxed local path after a clean scan. |
| Q106 | Implemented. Replacement before submission creates a new immutable version and recalculates completeness. |
| Q107 | Implemented. Replacement after submission is a supplemental document version linked to the immutable submission. |
| Q108 | Implemented. Document reuse creates a new application link and does not broaden access. |
| Q109 | Implemented. An expired document stays in submitted history and current completeness asks for a replacement. |
| Q110 | Implemented. A sanitized display name is stored separately from the opaque object key. |
| Q111 | Implemented. Download and export require purpose-bound permission, a checksum, an audit event, and rate limits. |
| Q112 | Implemented. Progress is shown by section and participant, not by a percentage alone. |
| Q113 | Implemented. Completeness is a deterministic evaluation of required fields, attestations, clean documents, and disclosures. |
| Q114 | Enforced invariant. Completeness means required material is present and does not mean the applicant is eligible or approved. |
| Q115 | Implemented. Conditional questions use versioned server-side rules and do not branch on a protected trait. |
| Q116 | Implemented. The server is authoritative for validation, and the client only assists with accessible errors. |
| Q117 | Implemented. A policy-approved not-applicable value is distinct from a blank answer and carries no automatic penalty. |
| Q118 | Implemented. A deadline uses the property time zone, shows a countdown, and does not expire silently. |
| Q119 | Implemented. A deadline extension records authority, reason, the new deadline, and an audit event. |
| Q120 | Implemented. A requirement change during a draft re-evaluates openly and preserves prior answers. |
| Q121 | Implemented. Readiness lists blocking items by participant and section with links to the relevant part. |
| Q122 | Enforced invariant. A completeness override cannot fabricate consent or a clean document scan. |
| Q123 | Implemented. Warnings, blocking omissions, conflicts, expired evidence, and prohibited data stay distinct. |
| Q124 | Implemented. An invitation is a high-entropy expiring capability tied to one application, role, and destination. |
| Q125 | Implemented. The primary applicant or authorized staff may invite a participant within role compatibility rules. |
| Q126 | Implemented. Invitation delivery is provider-neutral and records queued, failed, or suppressed truth through the local fake. |
| Q127 | Enforced invariant. Before acceptance, an invitation shows only minimal context, role, expiry, and a support path. |
| Q128 | Implemented. A wrong-recipient invitation is revoked, the capability is rotated, and a corrected invitation may be issued. |
| Q129 | Enforced invariant. One person has one active accepted compatible role on an application, with no silent identity link. |
| Q130 | Implemented. Each adult attests individual sensitive sections, and the primary applicant owns shared household sections. |
| Q131 | Implemented. A material edit to a shared household fact requires re-attestation by the affected required participants. |
| Q132 | Implemented. Reminders are consent and suppression aware, deduplicated, and delivered only through the synthetic local adapter. |
| Q133 | Implemented. An expired invitation ends access, and an authorized resend creates a new capability. |
| Q134 | Implemented. A participant may withdraw participation without deleting immutable evidence. |
| Q135 | Implemented. Submission is one transactional command that revalidates policy, listing, completeness, consents, documents, and versions. |
| Q136 | Implemented. The immutable snapshot includes roles, answers, policy and disclosure versions, listing context, document hashes, and timestamps. |
| Q137 | Implemented. Relational history is kept together with a schema-versioned serialized snapshot hash. |
| Q138 | Implemented. The applicant receipt contains the reference, time, property context, and next steps, without internal review data. |
| Q139 | Enforced invariant. A submitted application cannot be edited in place. |
| Q140 | Implemented. An applicant correction creates an immutable supplement and recalculates the current review projection. |
| Q141 | Implemented. A missing-item request names the requirement, objective reason, due date, owner, and participant. |
| Q142 | Implemented. Withdrawal is an explicit command that stops future processing and retains history. |
| Q143 | Enforced invariant. Staff may withdraw only for an administrative reason such as a duplicate or applicant request, not as a housing decision. |
| Q144 | Implemented. Reopen is a governed new episode that preserves the withdrawal history. |
| Q145 | Implemented. The same idempotency key and fingerprint return the original receipt, and a changed payload conflicts. |
| Q146 | Implemented. Version checks and a row lock prevent a concurrent submit, withdrawal, or document change from writing an inconsistent snapshot. |
| Q147 | Implemented. Each supplement has its own hash and does not alter the prior snapshot. |
| Q148 | Enforced invariant. Unverifiable snapshot evidence fails closed and blocks the downstream handoff. |
| Q149 | Implemented. The staff queue optimizes completeness, document, deadline, and exception work rather than desirability. |
| Q150 | Implemented. The review screen shows roles, the listing snapshot, answers, clean documents, completeness, requests, and the timeline. |
| Q151 | Implemented. Staff notes are objective, authored, classified, and auditable, without an applicant-quality flag. |
| Q152 | Implemented. Verification is recorded per field or document with method, verifier, and time. |
| Q153 | Implemented. A discrepancy records the conflicting facts, owner, clarification request, and resolution history. |
| Q154 | Implemented. A missing-item notice uses transactional delivery plus an in-app task and omits sensitive details from the preview. |
| Q155 | Enforced invariant. Staff cannot request an arbitrary document such as a government identifier. |
| Q156 | Enforced invariant. Assignment follows scope, capacity, and deadline, and does not use applicant traits or expected outcome. |
| Q157 | External acceptance gate. Owner-level exceptions cover material policy, systemic risk, unusual retention, and reserved business decisions. |
| Q158 | Enforced invariant. Phase 12 cannot approve, deny, score, or recommend an applicant. |
| Q159 | Implemented. Ready for screening is only a technical handoff after an explicit authorized command. |
| Q160 | Implemented. The timeline records initiation, disclosures, invitations, saves, documents, submission, requests, withdrawal, and handoff. |
| Q161 | Enforced invariant. Requirements are uniform and property-policy driven, without protected-class proxies or selective friction. |
| Q162 | Implemented. A reasonable-accommodation request is a separate privacy-limited path and does not block ordinary progress. |
| Q163 | Enforced invariant. An assistance animal is outside ordinary pet fees and pet scoring. |
| Q164 | Implemented. The applicant and staff surfaces target WCAG 2.2 AA behavior, including keyboard use, focus, labels, and status text. |
| Q165 | Implemented. Locale-aware content records language provenance, and only reviewed translations are shipped. |
| Q166 | Implemented. An assisted channel uses the same requirements, attributes the staff actor, and does not impersonate the applicant. |
| Q167 | Implemented. Low-bandwidth use relies on small resumable requests, durable drafts, and printable requirements. |
| Q168 | Implemented. Funnel measurement uses coarse operational steps and does not collect protected-class traits for analytics. |
| Q169 | External acceptance gate. A deviation that affects equitable access needs owner policy plus qualified legal and fair-housing review. |
| Q170 | Enforced invariant. Purpose limitation and data minimization govern every field, document class, role, and lifecycle state. |
| Q171 | Implemented. Retention rules are versioned by record class, outcome, and hold, with a synthetic 30-day draft default. |
| Q172 | Implemented. A legal hold suspends conflicting deletion for the identified application and records authority and scope. |
| Q173 | Implemented. An access request is authenticated and produces a scoped export after review. |
| Q174 | Implemented. A correction after submission appends a supplement and leaves the original snapshot intact. |
| Q175 | Implemented. A deletion request is checked against holds and obligations, and a minimal non-sensitive receipt is kept. |
| Q176 | Implemented. An export packages human-readable and structured data separately from documents, with an integrity manifest. |
| Q177 | Enforced invariant. Analytics exclude field values, free text, document contents, identifiers, and secrets, and honor GPC. |
| Q178 | Implemented. Privacy incident evidence is tamper-evident access, export, and deletion history without copying sensitive content into logs. |
| Q179 | Enforced invariant. Acceptance data is synthetic, and de-identified reuse requires a documented standard that this phase does not claim. |
| Q180 | Enforced invariant. Authorization is server-enforced with forced row security, organization scope, participant ownership, and deny by default. |
| Q181 | Implemented. Unauthenticated start uses an opaque short-lived single-purpose capability with server-side state and rate-relevant bounds. |
| Q182 | Enforced invariant. Sensitive identifiers are avoided, and any later secret field must use envelope encryption and purpose-bound reads. |
| Q183 | Enforced invariant. A service principal may only run a narrow scan, retention, delivery, or projection task. |
| Q184 | Enforced invariant. No actor or an invalid context returns no protected rows, and a forged organization cannot cross scope. |
| Q185 | Enforced invariant. Secrets stay out of source, evidence, browser payloads, and logs, and local fakes are development-only. |
| Q186 | Enforced invariant. File handling rejects mismatched magic, suspicious active content, path tricks, and unsafe download behavior. |
| Q187 | Enforced invariant. Web commands enforce origin-safe mutations, injection-safe queries, replay rules, and request limits. |
| Q188 | Implemented. Abuse controls use bounded uploads and do not force an inaccessible challenge on every applicant. |
| Q189 | Enforced invariant. Staff see sensitive application material only through an authorized purpose, with redaction by default and an audit event. |
| Q190 | Explicitly deferred to the encryption design. Key rotation metadata, dual-read, and old-key retirement apply if a sensitive field is later stored. |
| Q191 | Implemented. Independent review must resolve every critical or high finding before local acceptance. |
| Q192 | Implemented. Phase 13 receives a versioned immutable handoff package and event, not a live screening call. |
| Q193 | Enforced invariant. Phase 12 does not call screening, credit, criminal, income-verification, or decision providers. |
| Q194 | Enforced invariant. An application attestation does not create a lease, signature envelope, deposit obligation, tenancy, or possession right. |
| Q195 | Implemented. Transactional application, invitation, missing-item, and status notices use the outbox and the local fake, with no marketing. |
| Q196 | Implemented. Operational metrics cover starts, saves, submissions, withdrawals, invitations, scans, backlog, delivery, errors, and latency without sensitive payloads. |
| Q197 | Implemented. Dashboards emphasize backlog, blockers, scan failures, policy-version exposure, and privacy exceptions within the actor's scope. |
| Q198 | Enforced invariant. A product experiment cannot silently change required facts, disclosures, or access. |
| Q199 | Enforced invariant. Production AI does not score, summarize, or extract substantive application content. |
| Q200 | Implemented. Commands are transactional with idempotency and optimistic concurrency, and projections must not invent completion. |
| Q201 | Implemented. The benchmark proves at least 1001 properties, 3003 spaces, 25000 prospects, 50000 inquiries, 25000 applications, 50000 participants, and 100000 document records. |
| Q202 | Implemented. Representative p95 targets are under 500 ms for draft save and upload finalization, under 300 ms for detail and queue, under 500 ms for completeness, and under 750 ms for the submission command. |
| Q203 | Implemented. Operations keep correlation, redacted logs, bounded retry, and truthful degraded states for storage, scanner, and delivery outages. |
| Q204 | Implemented. The Phase 12 contract and trace are published with the behavior that the validator checks. |
| Q205 | Implemented. Implementation stays on one authoritative contract, one migration order, and shared integration checkpoints. |
| Q206 | Enforced invariant. Acceptance uses deterministic synthetic applicants, households, documents, policies, and provider fakes only. |
| Q207 | Implemented. Automated tests cover domain rules, migration, contracts, row security, concurrency, uploads, privacy, jobs, and adversarial cases. |
| Q208 | Implemented. Connected browser evidence covers Chromium, Firefox, and WebKit at 320, 768, 1024, and 1440 pixels, with keyboard use and an axe scan. |
| Q209 | Implemented. The clean room migrates an empty database to the exact head, proves role flags and forced row security, and removes disposable resources. |
| Q210 | Implemented. Governance evidence includes answer validation, secret and dependency checks, migration lineage, and an independent review record. |
| Q211 | Implemented. Work stays on cursor/phase-12-applications, binds evidence to the behavior commit, and merges only through the protected workflow. |
| Q212 | Implemented. The acceptance checker has local and pull-request modes for P12-R0 through P12-R18 and exits 0 only when the selected verdict is proven. |
| Q213 | Implemented. Evidence names and digests the tested behavior commit, and a later harness-only change must be classified. |
| Q214 | Implemented. Ordinary failures are repaired and rerun until every locally controllable gate passes. |
| Q215 | External acceptance gate. Hosted, stakeholder, legal, fair-housing, privacy, real-data, provider, production security, and production deployment verdicts stay separate. |
| Q216 | External acceptance gate. Work stops for Nathan only for a genuine user-controlled blocker such as missing account ownership or an unresolved material policy conflict. |
| Q217 | Implemented. Local completion requires the traced decisions, the exact migration head, forced row security, green exact-head and merged-main checks, and a clean synchronized main. |

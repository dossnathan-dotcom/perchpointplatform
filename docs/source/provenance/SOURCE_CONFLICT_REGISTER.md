# Source Conflict Register

Precedence: directive decisions > approved roadmap > platform vision > discovery statements > accepted Phase 0 evidence > current code > recommendation.

Source paths:
- Directive: `docs/source/provenance/DIRECTIVE_REFERENCE.md`
- Closure directive: `docs/source/provenance/CLOSURE_DIRECTIVE_REFERENCE.md`
- Roadmap: `docs/source/normalized/ENTERPRISE_DELIVERY_ROADMAP.md`
- Platform Vision: `docs/source/normalized/PLATFORM_VISION.md` (authoritative PDF extraction)
- Provisional historical text:
  `docs/source/normalized/PLATFORM_VISION_PROVISIONAL.md` (non-authoritative)
- Discovery: `docs/source/normalized/DISCOVERY_MEETING_TRANSCRIPT.md`
- Phase 0 evidence: `docs/phase0/README.md`

## CONFLICT-001 — Listing channels
- Claims: roadmap pages 6–7 and discovery pages 12–14 propose Zillow/Facebook coexistence or
  syndication; Platform Vision page 1 specifies a public leasing website but does not require
  syndication; directive §4.1/§4.3 prohibits current syndication and makes the HawkVision site
  exclusive.
- Consequence: product/workflow/data integration.
- Safe assumption: no Zillow/Facebook implementation; retain conflict as historical context.
- Decision owner: Faruk (business), Nathan (implementation).
- Continue safely: Yes. Status: resolved by higher-precedence directive.

## CONFLICT-002 — Innago lifecycle
- Claims: roadmap page 10 and discovery pages 9/19/28 allow coexistence; directive §4.1 requires migrate, reconcile, read-only archive, and retire.
- Consequence: migration, payments, operating procedure.
- Safe assumption: coexistence is a bounded migration state only.
- Decision owner: Faruk/Nathan/accounting specialist.
- Continue safely: Yes. Status: resolved by higher-precedence directive.

## CONFLICT-003 — Incremental “MVP” framing
- Claims: discovery pages 22–29 proposes an MVP; directive §9 prohibits using MVP to diminish complete scope.
- Consequence: acceptance and commercial scope.
- Safe assumption: phases are evidence gates, not scope reduction.
- Decision owner: Faruk and Nathan.
- Continue safely: Yes. Status: resolved.

## CONFLICT-004 — Accounting authority
- Claims: roadmap/discovery discuss Short Landlord and operational accounting visibility;
  Platform Vision page 2 assigns resident-ledger and reconciliation support to HawkVision's
  platform but does not claim GL/tax authority; directive states formal accounting software
  remains authoritative for GL, tax, close, and finalized statements.
- Consequence: financial reporting and legal/accounting reliance.
- Safe assumption: PerchPoint is operational accounting only.
- Decision owner: Faruk and accounting specialist.
- Continue safely: Yes for governance; provider and accounting platform remain open. Status: open detail, boundary resolved.

## CONFLICT-005 — Official communications
- Claims: discovery permits transitional WhatsApp use; Platform Vision page 2 places email/text
  delivery providers behind the platform; directive §4.1 requires official communications in or
  captured by PerchPoint.
- Consequence: audit, consent, records, adoption.
- Safe assumption: transitional channels are non-authoritative and material content must be captured.
- Decision owner: Ann/Faruk; counsel for recording and retention.
- Continue safely: Yes. Status: resolved at policy level.

## CONFLICT-006 — Owner spelling
- Claims: source PDFs use `Farouk`; directive approves `Faruk Atmaca`.
- Consequence: identity, signatures, traceability.
- Safe assumption: use `Faruk` in canonical policy and preserve quoted source wording.
- Decision owner: Faruk.
- Continue safely: Yes. Status: resolved provisionally by directive.

## CONFLICT-007 — Platform Vision provenance
- Claims: provisional text was pasted before the mandatory original PDF was accessible. The
  authoritative two-page PDF is now byte-preserved and directly extracted; comparison found no
  material wording discrepancy.
- Source/page references: authoritative `PLATFORM_VISION.md`, pages 1–2; historical
  `PLATFORM_VISION_PROVISIONAL.md` has no page authority.
- Affected domains: source integrity, product traceability, acceptance.
- Business/technical consequence: resolved source-ingestion blocker; provisional text remains
  excluded from authority.
- Safe assumption: cite the preserved PDF extraction; retain provisional text only for history.
- Decision owner: Nathan, technical acceptance.
- Blocking status: no longer blocks source acceptance or later-phase planning; it does not
  authorize Phase 2 implementation, and production activation remains independently gated.
- Resolution status: **resolved** by matching pre/post SHA-256, 2/2 page extraction, and
  deterministic regeneration.

## CONFLICT-008 — Physical hierarchy versus relationship model
- Claims: Phase 0 `docs/phase0/CANONICAL-MODEL.md` presents
  `Organization → OwnershipEntity → Property → Building → Unit` and stores
  `ownership_entity_id` on `Property`. Nathan-approved Phase 2 architecture requires
  physical containment (`property → building → leasable space`) to remain distinct from
  effective-dated ownership, management, portfolio membership, and occupancy relationships.
- Consequence: schema evolution, fixtures, queries, and UI hierarchy views.
- Safe assumption: preserve existing fixture UUIDs; treat current
  `ownership_entity_id` as a current-effective projection; add explicit relationship
  records in Phase 2 contracts (`0.2.0`) rather than silently rewriting Phase 0 fixtures.
- Decision owner: Nathan (architecture).
- Blocking status: does not block planning; blocks implementation until this plan is approved.
- Resolution status: **resolved for planning** by higher-precedence Phase 2 architecture.

## CONFLICT-009 — Combined unit status versus separated restriction states
- Claims: Phase 0 `Unit.status` is `available | occupied | unavailable`. Approved Phase 2
  architecture requires separate unit condition, occupancy, availability, publication,
  maintenance-restriction, and legal-restriction states.
- Consequence: listing publication, inquiry eligibility, and derived household journeys.
- Safe assumption: Phase 0 `status` remains a derived public/read projection; new fields
  become the write-authoritative states. Existing fixture statuses map to occupancy and
  availability only.
- Decision owner: Nathan.
- Blocking status: does not block planning.
- Resolution status: **resolved for planning** by higher-precedence Phase 2 architecture.

## CONFLICT-010 — Adult individual accounts versus default primary access
- Claims: `PP-AUTH-010` requires each adult resident to use an individually authenticated
  account linked to a household. Approved Phase 2 direction uses one primary resident
  account by default, with additional access only through explicit authorization, and
  never shared household passwords.
- Consequence: identity provisioning, household UX, and authorization tests.
- Safe assumption: no shared household password; default provisioning creates one primary
  individual account; additional adult portal access requires an explicit individual
  account; occupants without portal access remain occupants, not users.
- Decision owner: Nathan (technical), Ann (operational fit).
- Blocking status: neither technical implementation of the reference slice nor production
  identity activation is blocked by this interpretation.
- Resolution status: **resolved by compatible interpretation**; production identity remains
  later-phase (`PP-AUTH-011`).

## CONFLICT-011 — Phase 3 hosted evidence timing
- Claims: the approved Q1–Q174 register still requires hosted staging, hosted PITR,
  hosted recovery measurement, and paid monitoring before those operational gates
  can be called passed. On 2026-09-26 Nathan Doss directed that no paid subscription,
  paid trial, or billing-backed provider feature be activated now.
- Consequence: Phase 3 acceptance must separate local engineering evidence from
  hosted operational evidence. The underlying production requirements stay in force.
- Safe assumption: implement and test the local, container, CI, and free-account
  controls now. Record hosted execution as owner-deferred, not as a failed build
  and not as a deleted requirement.
- Decision owner: Nathan for the timing directive. Faruk remains the billing owner
  for any later paid activation.
- Resolution status: **resolved as a timing decision** by PP-DEC-059. Q1–Q174 wording
  is unchanged.

## CONFLICT-012 — Phase 0 workspace tabs and Phase 4 navigation labels
- Claims: accepted Phase 0 role previews use labels such as Operations Console and
  Operational inbox. The Phase 4 directive approves a different navigation vocabulary
  for the same roles.
- Consequence: route stability and the meaning of the sidebar.
- Safe assumption: keep every existing slug and label, and append the approved
  destinations. The URL role remains a preview label, not authority.
- Decision owner: Nathan.
- Resolution status: **resolved by compatible routes** under PP-DEC-063.

## CONFLICT-013 — Emergent runtime scripts and Phase 4 security
- Claims: the Emergent public HTML loaded Google Fonts, `assets.emergent.sh`, and a
  PostHog session-replay snippet. Phase 4 requires self-hosted or system fonts, no
  third-party scripts, and no session replay.
- Consequence: content security policy and the public entry document.
- Safe assumption: remove those runtime dependencies and keep the visual palette.
- Decision owner: Nathan.
- Resolution status: **resolved by removal** under PP-DEC-065 and PP-DEC-068.

## CONFLICT-014 — Emergency preservation ceiling
- Claims: `PP-MAINT-007` retains a provisional historical $2,500 Ann emergency limit.
  Approved Phase 6 Q118 limits Ann's immediate life-safety or property-preservation authority
  to $1,200 inclusive and requires documented act-and-notify escalation above that amount.
- Consequence: applying the older provisional amount would create unauthorized spending
  authority and contradict the ordinary Phase 6 owner threshold.
- Safe assumption: enforce the narrower $1,200 Phase 6 ceiling; do not fabricate ordinary
  approval above it. Preserve unavoidable imminent-harm response as a separately documented
  act-and-notify event.
- Decision owner: Faruk (business authority); Nathan implements the policy.
- Continue safely: yes, because the narrower rule reduces authority and Q118 has higher Phase 6
  precedence.
- Resolution status: **resolved for Phase 6 local implementation** by Q118. Faruk remains the
  acceptance authority for production activation.

Existing listing, accounting, communications, provider, human-approval, and
production-activation boundaries remain controlling.

## CONFLICT-015 — Roadmap phase count display
- Claims: the requested execution index lists 26 phases numbered 1–26. The master roadmap
  source also contains Phase 0 and a later tail, Phases 27–30.
- Consequence: documentation display count only. No product scope change.
- Safe assumption: Phase 0 stays an inherited prerequisite, Phases 1–26 stay the requested
  implementation index, and Phases 27–30 stay future work outside Phase 7. Do not renumber
  or delete either source.
- Decision owner: Nathan.
- Continue safely: yes. Status: recorded, not blocking Phase 7.

## CONFLICT-016 — Phase 8 listing distribution
- Claims: roadmap Phase 8D describes Zillow and Facebook coexistence. The approved Phase 8
  directive makes the HawkVision site the exclusive listing destination and defers discovery
  and syndication to later phases that are not authorized now.
- Consequence: publication and integration scope.
- Safe assumption: Phase 8 publishes immutable snapshots to the HawkVision public site only.
  No feed, marketplace, or external listing workspace is implemented.
- Decision owner: Nathan for this implementation; Faruk retains production publication authority.
- Continue safely: yes. Status: resolved for Phase 8 local implementation by Q1 and Q91.

## CONFLICT-017 — Pricing materiality versus the procurement ceiling
- Claims: the accepted $1,200 threshold governs commitments and procurement. Phase 8 Q40 and
  Q74 require configurable absolute and percentage bands for rent and fee materiality.
- Consequence: who may change asking rent without owner approval.
- Safe assumption: do not reuse $1,200 as a rent-change threshold. Seed only synthetic bands
  of 10 percent or 15000 minor units. Those bands are not production policy.
- Decision owner: Faruk for production policy; Nathan for the local synthetic control.
- Continue safely: yes. Status: resolved for Phase 8 local implementation. Stakeholder
  acceptance of the bands remains separate.

## CONFLICT-018 — Phase 9 distribution versus early marketplace examples
- Claims: early roadmap text names Zillow, Facebook, feeds, or advertising as listing
  distribution. Approved Phase 8 and Phase 9 decisions make the HawkVision website the
  exclusive listing destination.
- Consequence: discovery and distribution scope.
- Safe assumption: Phase 9 propagates eligible snapshots only to HawkVision-owned search,
  detail, sitemap, cache, link-preview, and health surfaces. External syndication is
  disabled by policy and is not implemented as dormant vendor code.
- Decision owner: Faruk Atmaca for any future channel reversal; Nathan for this local
  implementation.
- Continue safely: yes. Status: resolved for Phase 9 local implementation by Q1 and Q4.

## CONFLICT-019 — Phase 10 CRM versus early marketplace and lead examples
- Claims: early roadmap text describes external lead marketplaces, syndication, or a generic
  CRM. Approved Phase 10 decisions keep HawkVision website intake and authorized manual entry
  as the only acquisition paths, and they keep the $1,200 figure in procurement rather than
  prospect priority.
- Consequence: inquiry scope and operational priority.
- Safe assumption: Phase 10 stores prospects, inquiries, consent, assignment, clocks, and next
  actions in PerchPoint. It does not ingest an external lead workspace or rank people by
  predicted housing value.
- Decision owner: Faruk Atmaca for any future channel reversal; Nathan for this local
  implementation.
- Continue safely: yes. Status: resolved for Phase 10 local implementation by Q1, Q6, and Q11.

## CONFLICT-020 — Phase 11 canonical scheduling versus early marketplace calendars
- Claims: early roadmap examples mention marketplace scheduling, personal calendars as the
  system of record, or self-guided lockbox entry. Approved Phase 11 decisions keep PerchPoint
  as the canonical appointment record and keep provider calendars as mirrors and busy inputs.
- Consequence: showing identity, overlap control, and access safety.
- Safe assumption: Phase 11 books only from a server-issued capability, rejects self-guided
  entry, and uses a fake calendar adapter. It does not activate a live calendar provider.
- Decision owner: Faruk Atmaca for any future provider or access reversal; Nathan for this
  local implementation.
- Continue safely: yes. Status: resolved for Phase 11 local implementation by Q1, Q3, and Q13.

## CONFLICT-021 — Phase 12 applications versus screening, fees, and leases in the form
- Claims: early examples collect an application fee, ask screening questions, or treat the
  submitted form as a lease or housing decision. Approved Phase 12 decisions keep PerchPoint
  as the application record, model a fee without collecting it, and leave screening, adverse
  action, leases, and payments to later phases.
- Consequence: application completeness, document handling, and the Phase 13 boundary.
- Safe assumption: Phase 12 stores a household application, disclosures, and scanned documents.
  It does not score an applicant, call a screening provider, or create a lease.
- Decision owner: Faruk Atmaca for any future screening or payment reversal; Nathan for this
  local implementation.
- Continue safely: yes. Status: resolved for Phase 12 local implementation by Q1, Q7, and Q158.

## CONFLICT-022 — Phase 13 decisions versus provider scores and live screening
- Claims: early examples treat a screening provider score as the housing decision or collect a
  report during the application. Approved Phase 13 decisions keep PerchPoint as the decision
  record, use deterministic provider fakes, and leave live pulls, leases, and payments outside
  this phase.
- Consequence: who may decide, which products may be ordered, and what Phase 14 may receive.
- Safe assumption: Phase 13 records a human decision from normalized fake evidence. It does not
  call a live screening provider, store a full government identifier, or create a lease.
- Decision owner: Faruk Atmaca for any future provider or criminal-history activation; Nathan
  for this local implementation.
- Continue safely: yes. Status: resolved for Phase 13 local implementation by Q4, Q5, and Q110.

## CONFLICT-023 — Phase 14 lease execution versus live signatures, deposits, and resident portals
- Claims: early examples send a lease to a live signature vendor, collect a deposit, or mark an
  applicant as a resident when a packet is sent. Approved Phase 14 decisions keep PerchPoint as
  the execution record, use a deterministic signature fake, record a deposit obligation without
  moving money, and activate a resident only after the package is executed.
- Consequence: what may be signed locally, what a deposit status means, and what Phase 15 may receive.
- Safe assumption: Phase 14 consumes an approved Phase 13 handoff and does not rewrite it. It does
  not call a live signature or payment provider, post a ledger, or open a resident portal.
- Decision owner: Faruk Atmaca for template approval and material deviations; Nathan for this
  local implementation.
- Continue safely: yes. Status: resolved for Phase 14 local implementation by Q1, Q5, and Q13.

## CONFLICT-024 — Phase 15 resident portal versus later financial, maintenance, and messaging systems

- Claims: a resident portal could show balances, accept payments, create work orders, or deliver
  messages. Approved Phase 15 decisions make membership, invitations, documents, preferences, and
  requests authoritative, and keep later domains as labeled non-authoritative demo previews.
- Consequence: what a resident can see or request, and what Phase 16 and later phases still own.
- Safe assumption: Phase 15 consumes a Phase 14 activation and does not rewrite it. It does not
  post a ledger, collect money, create a maintenance case, or claim a message was delivered.
- Decision owner: Faruk Atmaca for resident-access policy; Ann Springer for delegated operations;
  Nathan for this local implementation.
- Continue safely: yes. Status: resolved for Phase 15 local implementation by Q1, Q3, and Q154.


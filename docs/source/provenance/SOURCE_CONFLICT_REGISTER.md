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

Existing listing, accounting, communications, provider, human-approval, and
production-activation boundaries remain controlling.

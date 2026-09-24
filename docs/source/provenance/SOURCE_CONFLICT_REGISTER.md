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

No new conflict was created: the authoritative PDF materially matches the provisional wording
and does not contradict higher-precedence approved decisions. Existing listing, accounting,
communications, provider, human-approval, and production-activation boundaries remain
controlling.

# Phase 16 review findings

Reviewed against behavior commit `96487c9d5920466b062cd1cce964e69342413fe8`. `python scripts/phase16_review.py` reported no critical or high findings. Reviewer identity: `phase16-independent-review`.

## Resolved

- A resident account opens only from an active Phase 15 membership. A second account is rejected.
- Journal lines use integer minor units and stay append-only. A typed balance is rejected.
- A subsidy share does not increase resident debt, and a deposit hold is not applied to rent.
- A synthetic settlement balances applied and unapplied amounts and does not move money.
- A reversal preserves the original lines, and a dispute does not rewrite the journal.
- An unrelated organization is denied, and a runtime session with no actor sees no journal rows.

## Separate verdicts

This technical review does not grant hosted Supabase acceptance, stakeholder acceptance, qualified legal or fair-housing acceptance, privacy-counsel acceptance, screening-provider acceptance, real-data migration acceptance, or production deployment.

No critical or high finding remains open inside Phase 16. Phase 17 was not started.

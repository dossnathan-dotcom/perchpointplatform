# Phase 16 walkthrough

Synthetic personas only. No real resident, bank, processor, or accounting system is connected.

1. Ann Synthetic, `ann.synthetic@example.com`, opens a household after a Phase 14 activation and accepts the invitation for Casey Synthetic.
2. The same operator opens one USD resident account for that active membership. A second open is rejected.
3. A recurring rent occurrence posts a balanced journal entry in minor units. Repeating the occurrence does not create a second charge.
4. An assistance share posts to the subsidy position and does not increase resident debt.
5. A deposit hold stays distinct from rent and is not applied to the receivable.
6. A synthetic settlement allocates to the open receivable. Any remainder is a prepayment. No processor is called and `money_moved` stays false.
7. A reversal adds a new journal entry. The original lines stay in place. A second reversal of the same charge is rejected.
8. A dispute records a submitted question and does not delete or rewrite journal lines. It is not a legal conclusion.
9. A statement version records the derived due amount and is marked `SYNTHETIC OPERATIONAL STATEMENT — NOT A TAX RETURN — NOT A FORMAL GENERAL LEDGER`. It is not delivered by email or paper.
10. Closing the account period rejects a later charge. The opening-balance manifest stays a dry run with `real_values_activated=false`.
11. Resident Synthetic and Isolation Synthetic cannot open the account. A session with no actor sees no journal rows.
12. Live payment and typed-balance commands stay closed.

`python scripts/phase16_demo.py --verify` checks this packet on a local target.

# Phase 19 architecture

Recorded October 12, 2026. This is the local reconciliation implementation. It is not production activation and it does not open the deferred maintenance phase.

`CONFLICT-027` and `docs/plans/phase18/DECISIONS.md` assign Phase 19 to bank and payout reconciliation, closing, and exports. The roadmap's omnichannel maintenance phase stays deferred. This phase does not add a second ledger.

A processor or bank line is an observation in integer USD minor units. Exact two-decimal strings are accepted. Floats and other currencies are rejected. A preview writes nothing. A duplicate source identity replays. A different amount conflicts. Pending and posted stay distinct. A fault before commit leaves no line.

A bank row does not post a resident settlement or a subsidy. An assistance batch and a historical receipt can be linked and stay unposted. Unknown inflows stay unidentified. An internal transfer is not revenue. Two allocations cannot consume the same line capacity.

Ann can search the queue, take ownership, and meet a version conflict. Faruk reads one briefing snapshot: decisions, exposure, owners, owed, processing, paid out, at the bank, and stale sources. The October demonstration remains $4,275 past due, Sycamore House, Brookside House, and Avery Morgan at Maple Court 101 with $0 due. Acknowledgement does not resolve the snapshot. A failed refresh returns the previous snapshot.

A preparer drafts a close. A different reviewer issues the next version. The issued packet hash does not change when a later line arrives.

`real_values_activated` stays false. `money_moved` stays false.

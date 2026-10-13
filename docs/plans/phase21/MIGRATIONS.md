# Phase 21 migration

`0067_phase21_calls` revises `0066_phase20_maintenance`. It is forward-only. The nine new tables force row-level security. Runtime grants are select, insert, and update on the mutable tables. Capability inserts use `SET LOCAL ROLE perchpoint_definer`.

`call_interactions` is the parent. Legs, events, notes, callbacks, and rejections are children. There is no raw payload column and no recording column. `money_moved` and `real_values_activated` stay false.

The Phase 20 clean room remains pinned at `0066`. Demo seeding skips call rows when the tables are absent.

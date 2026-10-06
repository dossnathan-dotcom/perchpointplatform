# Phase 8 acceptance report

Behavior commit: `bf314cb5349bd57ffc251f99b4c287ec6396f95e`.

`python scripts/phase8_evidence.py --all` recorded P8-R0 through P8-R16 as passed with exit code 0. The structured record is `test_reports/phase8/acceptance-state.json`. Each gate stores the command, the behavior commit, the exit code, and the SHA-256 of the captured output. Raw output is in `test_reports/phase8/logs/`.

P8-R11 backend result: 179 passed, 0 failed, 0 skipped. Frontend unit tests: 36 passed. Playwright `e2e/phase8-portfolio.spec.js`: 12 passed across Chromium, Firefox, and WebKit at 320, 768, 1024, and 1440 pixels, including the axe scan of `#main`. Benchmark cardinalities were 1,001 properties, 3,003 spaces, 3,003 prices, and 250,000 audit rows, with 1,001 properties visible to the runtime role. Inventory samples were 69.028, 68.210, and 69.304 ms. Detail samples were 71.158, 68.956, and 70.331 ms. Snapshot samples were 1.078, 0.945, and 0.925 ms. Errors and timeouts were 0. The benchmark database was dropped.

The clean room reached migration head `0036_phase8_availability`, confirmed ancestors `0035_phase7_property_visibility` and `0031_phase6_authz_remediation` (lineage length 36), recorded runtime `false,false` for superuser and bypassrls, forced row security on 98 of 98 enabled tables, and passed the same 179 backend tests before removing the clean-room containers and volumes.

P8-R17 passed for pull-request head `17c8b31481a4a56195dedc52502b6ac17dc1c9ee`. Required checks on that commit passed in [run 37488181606](https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/37488181606) (10 jobs) and the Phase 6 clean room passed in [run 37488181437](https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/37488181437) (1 job). CodeQL passed. Supabase Preview stayed skipped. P8-R18 is recorded from the merged main workflows.

Hosted Supabase, Faruk and Ann stakeholder acceptance, qualified legal and fair-housing review, real-data migration, and production deployment are not granted. Phase 9 was not started.

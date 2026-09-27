# Phase 5 acceptance

This record states what was executed. It does not grant hosted, business, or production acceptance. The sections through "Historical verdicts at pull request 23" record that earlier head. The definitive closeout section is the current local verdict.

## Source and governance

Executed and passed. `python scripts/validate_governance.py` reported 75 requirements and 75 decisions. `python scripts/validate_phase5_answers.py` reported 160 answers. `python scripts/validate_phase4_completeness.py` reported 64 destinations and 57 components.

## Local database and commands

Executed and passed. From `backend/`, `python -m pytest -q --tb=line` reported 109 passed and 25 warnings. The migration head asserted by the empty-database test is `0007_phase5_canonical`. Phase 5 tests covered cross-organization search, public-search isolation, EICAR quarantine, legal hold, formula-injection import blocking, exclusive relationship overlap, digest mismatch, missing-context denial, and runtime `UPDATE` denial on `audit_events`.

## Scale

Executed and passed for cardinality, then removed. `python scripts/phase5_scale.py` loaded disposable database `perchpoint_phase5_scale` and printed `properties=1000 spaces=3000 parties=5000 documents=25000 audit_events=250000`. The script then dropped that database. The 5,000 parties are person records. A superuser exact-title probe against 1,000 indexed properties measured p50 0.40 ms, p95 0.55 ms, and max 0.77 ms. That probe is not the permission-scoped fuzzy search at the full document and audit cardinality.

## Hosted staging

Externally blocked. `python scripts/phase5_staging_preflight.py` reported missing secret names `SUPABASE_DB_URL`, `SUPABASE_STORAGE_URL`, and `SUPABASE_STORAGE_KEY`. No values were printed. No production target was used.

## Pull request checks

Commit `9c39390d523508e8255a6d9f9f2b7bdbd04e05c8` passed push run https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36289071803 and pull-request run https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36289074582. The documentation commit `2df44fa4db7ad64f75ad27a882ee183e28a1984a` then failed pull-request browser job https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36292173610/job/108544238572: WebKit stayed on the homepage heading after one listing click while the hero text was rotating. The same SHA's push browser job passed. The listing test now scrolls the link into view, repeats the click once if the URL has not changed, and requires `/rentals/` before reading the listing heading. That correction is commit `9f48e8356b39cdaa0724d8c45d5643b8ccbe3188`. Its pull-request run https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36292621955 and push run https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36292618545 passed, including browser and phase4-performance. Supabase Preview remained a skipped hosted-branch integration and is not a required repository job.

## Merge

Pull request 23 merged with a merge commit. Final pull-request head `9f48e8356b39cdaa0724d8c45d5643b8ccbe3188`. Merge commit `73c170374e13476236c1d948c9cd8ac2262c478e`. Merged-main run https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36292926970 passed governance, contracts, backend, frontend, browser, secrets, supply-chain, containers, phase4-smoke, and phase4-performance. Clean-room Compose recovery was not re-run.

## Historical verdicts at pull request 23

These rows describe commit `73c170374e13476236c1d948c9cd8ac2262c478e` only. They are not the definitive closeout verdict.

| Verdict | Status |
| --- | --- |
| Source and governance | Executed and passed |
| Local technical | Not complete at that head. Clean-room recovery had not been re-executed. |
| Hosted staging | Externally blocked |
| Business and stakeholder | Not granted |
| Production readiness | Not authorized |

## Definitive closeout

Phase 5 implementation merged at `017f0ba88cf8381d60eace9a41469d3ae227c8c1` through pull request 25: https://github.com/dossnathan-dotcom/perchpointplatform/pull/25. Pull-request head `f180c09954ad6cd8df8e0bc3f8ba94f69e6606f3`. No later product commit supersedes that implementation. Alembic head is `0011_phase5_hold_guard`. Approved answers remain Q1–Q160 in `docs/plans/phase5/APPROVED_CUSTOMIZATION_ANSWERS.md`.

Pull-request checks passed on https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36342661578. Merged-main checks passed on https://github.com/dossnathan-dotcom/perchpointplatform/actions/runs/36343157087. Both runs concluded success for governance, contracts, backend, frontend, browser, secrets, supply-chain, containers, phase4-smoke, and phase4-performance. CodeQL succeeded. Supabase Preview stayed skipped.

The merged-main backend job installed only `backend/requirements.txt` on a clean runner. That file pins `motor==3.3.1` and `pymongo==4.6.3`. The job installed those versions and reported `119 passed, 3 skipped`. An earlier local collection failure, 18 times `ModuleNotFoundError: No module named 'motor'`, came from this machine's interpreter before it matched the committed pin. A later local run on the corrected interpreter, before the hold-guard test, reported 118 passed and 3 skipped. Neither number replaces the merged-main total. `backend/requirements-legacy.txt` is not installed by the app image or CI and is not a Phase 5 runtime dependency.

The three skipped tests are `tests/phase5/test_live_services.py::test_live_clamav_detects_eicar_and_outage_is_not_clean`, `tests/phase5/test_live_services.py::test_live_minio_presign_is_private_and_cleaned_up`, and `tests/phase5/test_live_journey.py::test_live_api_access_export_and_ocr`. Each skips unless `PHASE5_LIVE_SERVICES=1`, because the default suite does not start MinIO or ClamAV. The same behaviors were executed against Compose project `perchpoint-phase5-closeout`: live scan accepted text and PNG uploads, a presigned GET returned PNG magic, a range read matched those bytes, export returned a zip containing `manifest.json`, and the other organization received no content and no search hit. Those skips are not a substitute for that execution.

Search evidence stays in three classes. A manually terminated sequential-scan attempt is not a completed result. One completed `PHASE5_SCALE_RUNS=1` run exited 0, used a function scan of `perchpoint.search_rows`, measured fuzzy execution 11.949 ms and phrase execution 5.749 ms, and dropped its database. That run is query-plan evidence. The acceptance benchmark is the later three completed rounds (`PHASE5_SCALE_RUNS=3`, PostgreSQL 16.15, `perchpoint_runtime`, five warmups, 20 samples, one connection, actor and organization set with `set_config`, cardinalities 1000/3000/5000/25000/250000, cross-organization visibility 0, database dropped after each round, exit 0). Required p95 values were below 300 ms. Indexing lag on the same committed-write path as Q99 was under five seconds on all 20 party creates. Do not add the one-round plan timings to those three rounds.

The first Phase 5 browser run failed 3 and passed 3 against the pre-fix web image because center navigation cleared the session. Commit `f180c09` keeps the session across centers and still clears it when the role changes. That commit is an ancestor of `017f0ba`. The corrected source then passed 6/6 on Chromium, Firefox, and WebKit. The merged-main browser job passed on that same head.

The isolated Compose project migrated, seeded twice without duplicating accounts, ran as uid 10001, and recovered API readiness after PostgreSQL, MinIO, and ClamAV restarts. A custom-format dump of 174,764 bytes restored the then-current head, 3 properties, and 4 documents into a disposable database that was then dropped. The Phase 5 project was removed. The Phase 3 MinIO and ClamAV containers were still running. A legal hold blocks API disposition and raises `legal hold blocks mutation` for a runtime-role delete. Retention remains provisional and is not legal approval.

## Definitive verdicts

| Verdict | Status |
| --- | --- |
| Source and governance | Passed |
| Local technical | Passed on `017f0ba88cf8381d60eace9a41469d3ae227c8c1` |
| Hosted staging | Externally blocked. `SUPABASE_DB_URL`, `SUPABASE_STORAGE_URL`, and `SUPABASE_STORAGE_KEY` are not configured |
| Business and stakeholder | Pending |
| Production readiness | Blocked |

Phase 6 customization questions may be written. Phase 6 implementation, production deployment, live providers, and real tenant data remain outside this acceptance.

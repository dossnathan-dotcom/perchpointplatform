# Phase 14 acceptance report

Behavior commit: `64a7c215688963fffd0e7653ca46b5718e5f85db`.

`python scripts/phase14_evidence.py --all` recorded P14-R0 through P14-R16 as passed with exit code 0. The structured record is `test_reports/phase14/acceptance-state.json`. Each gate stores the command, the behavior commit, the exit code, and the SHA-256 of the captured output. Raw output is in `test_reports/phase14/logs/`.

Migration head exercised by the empty-database and clean-room gates: `0042_phase14_lease`. `0041_phase13_screening`, `0040_phase12_application`, `0039_phase11_showing`, `0038_phase10_inquiry`, `0037_phase9_discovery`, `0036_phase8_availability`, `0035_phase7_property_visibility`, and `0031_phase6_authz_remediation` are ancestors of that head.

P14-R17 and P14-R18 are not local gates. They are recorded after the protected pull request and the merged main workflows.

Hosted Supabase, Faruk and Ann stakeholder acceptance, qualified legal and fair-housing review, real-data migration, production providers, advertising, and production deployment are not granted. Phase 15 was not started. Live signature and payment providers were not activated.

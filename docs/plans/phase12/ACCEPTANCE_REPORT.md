# Phase 12 acceptance report

Behavior commit: `a2dff07f81bd2b03f7b645a4830187511b1bd294`.

`python scripts/phase12_evidence.py --all` recorded P12-R0 through P12-R16 as passed with exit code 0. The structured record is `test_reports/phase12/acceptance-state.json`. Each gate stores the command, the behavior commit, the exit code, and the SHA-256 of the captured output. Raw output is in `test_reports/phase12/logs/`.

Migration head exercised by the empty-database and clean-room gates: `0040_phase12_application`. `0039_phase11_showing`, `0038_phase10_inquiry`, `0037_phase9_discovery`, `0036_phase8_availability`, `0035_phase7_property_visibility`, and `0031_phase6_authz_remediation` are ancestors of that head.

P12-R17 and P12-R18 are not local gates. They are recorded after the protected pull request and the merged main workflows.

Hosted Supabase, Faruk and Ann stakeholder acceptance, qualified legal and fair-housing review, real-data migration, production providers, advertising, and production deployment are not granted. Phase 13 was not started. Screening, lease, and payment providers were not activated.

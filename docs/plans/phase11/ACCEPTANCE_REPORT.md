# Phase 11 acceptance report

Behavior commit: `ef2c0da23fcb2e96e549a9b12e3b609bf3eb86cc`.

`python scripts/phase11_evidence.py --all` recorded P11-R0 through P11-R16 as passed with exit code 0. The structured record is `test_reports/phase11/acceptance-state.json`. Each gate stores the command, the behavior commit, the exit code, and the SHA-256 of the captured output. Raw output is in `test_reports/phase11/logs/`.

Migration head exercised by the empty-database and clean-room gates: `0039_phase11_showing`. `0038_phase10_inquiry`, `0037_phase9_discovery`, `0036_phase8_availability`, `0035_phase7_property_visibility`, and `0031_phase6_authz_remediation` are ancestors of that head.

P11-R17 and P11-R18 are not local gates. They are recorded after the protected pull request and the merged main workflows.

Hosted Supabase, Faruk and Ann stakeholder acceptance, qualified legal and fair-housing review, real-data migration, production providers, advertising, and production deployment are not granted. Phase 12 was not started. Live calendar providers and self-guided access were not activated.

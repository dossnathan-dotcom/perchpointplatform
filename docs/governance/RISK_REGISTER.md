# Risk Register

- R-001 Resolved: authoritative Platform Vision preserved with matching pre/post checksum,
  complete 2/2-page extraction, and deterministic source validation; owner Nathan.
- R-002 High: role preview may be mistaken for auth; owner Nathan; preserve disclosures and future server/RLS gate.
- R-003 High: public synthetic contracts/people graph when flag enabled; owner Nathan; isolate preview and minimize payloads.
- R-004 Resolved for lockfile / Medium residual: canonical Yarn lockfile and frozen install pass;
  no CI workflow exists; owner Nathan.
- R-005 Resolved: tests derive repository root from module paths and pass from two working
  directories; legitimate Emergent `/app` deployment paths remain; owner Nathan.
- R-006 Medium: synthetic intake has no rate limit and accepts free text; owner Nathan; never expose as production.
- R-007 High: legal/accounting policies unapproved; owners Faruk/specialists; block activation.
- R-008 Medium: staff/tenant adoption may preserve fragmented channels; owner Ann; track migration/adoption.
- R-009 Medium: CRA/transitive dependency resolution emits documented peer, resolution, and
  deprecation warnings; owner Nathan; broad upgrades are deferred to an approved dependency cycle.
- R-010 Critical contamination control: synthetic development data must contain no real PII and
  must remain visibly synthetic; owner Nathan; scan fixtures, payloads, logs, and documents.
- R-011 Medium: Phase 2 implementation starting without plan approval or local PostgreSQL
  evidence; owner Nathan; stop conditions in `docs/plans/phase2/ACCEPTANCE.md`.
- R-012 Owner-deferred: hosted staging, hosted PITR, and live Sentry alerts are not
  evidence yet. The 2026-09-26 directive forbids paid activation. Owner Faruk for
  billing and Nathan for the later technical apply. Do not treat the deferral as
  production readiness.

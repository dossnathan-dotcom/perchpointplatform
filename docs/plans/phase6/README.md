# Phase 6 identity and access

Phase 6 adds local identity, server-custodied sessions, and relationship-aware authorization on top of the Phase 5 platform. Supabase Auth is the intended hosted provider. This repository uses a local Auth-compatible boundary and keeps business authority in PerchPoint.

The development JWT is not part of supported interactive startup. Tests may set `PHASE6_ALLOW_DEV_JWT=1` so earlier phases keep their isolated fixture.

## Status

Implementation is in progress on `cursor/phase-06-identity-access`. Local technical acceptance is not granted. Hosted Supabase, stakeholder acceptance, and production remain separate and are not granted.

## Decisions

`APPROVED_CUSTOMIZATION_ANSWERS.md` records Q1–Q160. `ANSWER_TRACEABILITY.md` maps each decision to the implementation that carries it.

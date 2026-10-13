# Phase 21 authorization

`calls.coordinate` is required for the desk, routing, notes, links, callbacks, and acknowledgement. Residents do not receive it. A hidden control is not authority.

Provider events are unauthenticated only after the Twilio request signature matches. The signature URL override is honored only when `PHASE3_ENVIRONMENT` is `local` or `test`. Recording, transcription, media, and voicemail-audio fields are dropped before persistence. No setting can turn a recording route on.

The callback worker authenticates with the existing service credential and `outbox.deliver`. It cannot acknowledge a call or accept a case.

Requirement: `PP-AUTH-001`, `PP-SEC-001`, `PP-COMM-001`.

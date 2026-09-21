# Migration, provenance and Innago retirement

No Innago access, export credentials or production records are required. No canonical database import runs in Phase 0.

## Contracts and artifacts
- `ImportBatch`: source system/file/checksum, organization, mapping version, staging/review/approval/import/rollback state, approval reference, rollback batch, immutable report checksum.
- `StagingRecord`: source record identity and row, mapped fields, validation result/issues, duplicate candidate, conflict, correction, approval, imported canonical reference, rejected flag.
- `Reconciliation`: source/observed/valid/rejected/duplicate/conflict totals, financial source vs valid staging totals, document counts/differences, reconciliation state.
- `MigrationReport`: rows, totals, stable report checksum, zero writes, rollback strategy.
- `contracts/fixtures/import-template.csv`: versioned headers.
- `contracts/fixtures/synthetic-innago.csv`: five synthetic rows.
- `contracts/fixtures/migration-report.json`: generated validation evidence.

## Staging behavior
`validate_import` validates exact header shape, row structure, required fields, nonnegative integer rent/document counts, currency syntax, organization/property/building chain and permitted unit use. Repeated source IDs or building/unit natural keys produce duplicate candidates. A natural-key match to an existing unit produces a conflict. Invalid/duplicate/conflicting records are excluded from valid staging totals, not silently merged.
Fixtures include one valid row, one duplicate, two invalid rows (negative amount and invalid hierarchy), one existing-unit conflict. “Valid” means suitable for staging review, **not approved for import**. No generated canonical ID or imported record exists for staged rows.

## Future import transaction (not executed)
Immutable source archive → checksum → versioned field mapping → staging → validation/deduplication/conflict queue → attributable correction → approval → canonical IDs + external mappings → financial/document control-total reconciliation → immutable report → cutover approval.
Corrections must reference original values and actor/reason rather than overwrite source evidence. Source IDs must remain in external-reference/provenance records. Manual conflict resolution and financial reconciliation require authorized reviewers.
Rollback is batch-scoped and repeatable; unreferenced nonfinancial insertions may be reversed with audit, while posted financial activity requires compensating entries—not erasing history. Preserve imported documents, rollback report and approvals under retention/legal hold.

## Intended end state
Innago/fragmented systems become temporary validation references, then read-only archives and retired systems after verified cutover. Do not build permanent dual-master synchronization as the product architecture.
Limitations: no source-file upload, canonical persistence, actual rollback, WORM report store, live source synchronization, entity-resolution algorithm or bank reconciliation. Checksums/frozen model instances alone do not make storage immutable.
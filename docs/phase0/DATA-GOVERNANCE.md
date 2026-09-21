# Data classification, documents, retention and jurisdiction policy

## Classification
| Class | Examples | Intended boundary |
|---|---|---|
| Public | Approved published inventory/terms | Approved publication only; seed labels until verified |
| Internal | Operational queues, assignments, configuration metadata | Organization/location/assignment/action scope |
| Confidential | Household records, financial documents, notices | Explicit role plus relationship and record access |
| Restricted | Identity documents, screening reports, privileged legal/security material | Sensitive-detail permission, purpose, attributable audit and step-up |

Do not include raw secrets, payment credentials or raw screening payloads in canonical/public records, logs, fixtures, browser bundles or audit diffs. Audit state must be redacted material changes, not full sensitive snapshots.

## Document classes
Application document, identity document, screening document, lease, addendum, notice, payment evidence, maintenance media, estimate, invoice, insurance policy, vendor credential, inspection, property record, legal document, communication attachment, migration archive.

`DocumentRecord` contains owner person/organization, related record IDs, scope, class, sensitivity, version, SHA-256 checksum, source, external storage reference, effective/expiration dates, retention rule, legal hold, access/download rule, deletion eligibility and audit requirement. No binary file contents or active storage URL is seeded.
Access and download are separate decisions. Future signed downloads must be short-lived, authorized and audited; no document route or upload service is provided now.

## Retention
`RetentionPolicy` has ID/version/class/jurisdiction, trigger event, `retention_days=null`, qualified-review status, legal-hold override and no deletion-without-review. All 17 classes have generated placeholders. **No legal retention period has been invented.** Counsel must define triggers, durations, legal-hold release, deletion verification, backups and provider copies before activation.

## Jurisdiction
`JurisdictionPolicy` supports country, state, county, municipality, property, unit type, lease type, effective/expiry dates, version, policy area, approved rule document and conflict review.
Areas: application disclosures, screening, fees, notices, deposits, late-payment rules, maintenance, retention, lease templates, emergency instructions.

Country/state/county/municipality are ordinary data, never global Ohio validators. Fixtures span Ohio, Kentucky and Pennsylvania. Other jurisdictions are structurally supported but their legal rules are not supplied or interpreted.
Do not assume “most specific wins” when laws conflict: jurisdiction resolution and preemption require qualified review. Future policy evaluation must preserve effective versions per action/lease/notice. Public 911 wording is explicitly US-context guidance; other countries require approved local emergency instructions.
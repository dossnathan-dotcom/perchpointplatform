# Real Information Activation Manifest

Phase 15 stores no real organization, resident, domain, phone, lease, or provider values. A later batch replaces synthetic configuration without an application source change.

| Item | Owner | Validation | Destination | Dependency | Approval |
| --- | --- | --- | --- | --- | --- |
| Legal and display identity | Faruk Atmaca | Non-empty display name and no secret field | Governed configuration version | Published successor version | Stakeholder |
| Public domains and origins | Nathan | Reserved example domains until the batch | Deployment configuration | DNS and allowed origins | Deployment |
| Email identities and templates | Ann Springer | Example addresses only in local mode | Outbox adapter | Verified sender, not a local fake | Operations |
| Phone, SMS, and after-hours routes | Ann Springer | Fictional numbers only | Support routing record | Telephony credential outside the database | Operations |
| Property, building, and space records | Faruk Atmaca | Canonical Phase 8 identifiers | Property projection | Real roster import | Real-data migration |
| Lease template and clause library | Faruk Atmaca | Sample marker required until legal approval | Published template version | Source-lease review | Qualified legal |
| Jurisdiction and applicability rules | Faruk Atmaca | Ambiguous rules block publication | Configuration resolution | Jurisdiction review | Qualified legal |
| Notices and privacy text | Faruk Atmaca | Effective date and version | Portal notices | Privacy and accessibility review | Qualified review |
| Provider selections | Nathan | Secret references only, never secret values | Deployment secret store | Separate provider gate | Production |
| Migration, rollback, and verdicts | Nathan | Dry run with `real_values_activated` false | `portal_manifest_runs` | Reconciliation plan | Each external verdict |

The local dry run rejects a payload that contains a secret, credential, password, or token field. It cannot activate real values. Production startup does not seed this demo.

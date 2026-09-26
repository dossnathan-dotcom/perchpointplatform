# Account ownership

Provisional identity: hawkvisionhomes@gmail.com. Nathan created the provider accounts. No paid plan has been purchased. MFA completion, organization names, and billing state were not supplied and are not invented here.

| Provider | Provisional owner | Permanent owner | Billing | Technical admin | Recovery | MFA | Secret storage | Status |
|---|---|---|---|---|---|---|---|---|
| GitHub | Nathan's existing user | HawkVision-controlled ownership before production | Not a paid upgrade in this phase | Nathan | Nathan | Not re-verified here | GitHub settings, no token in git | Repository exists and is public |
| Render | hawkvisionhomes@gmail.com | platform@hawkvisionhomes.com or another HawkVision domain mailbox | Faruk, later | Nathan, separate user | Faruk and Nathan, separate | Unknown | Company vault, later | Account reported created. Not activated |
| Supabase | hawkvisionhomes@gmail.com | Same permanent mailbox | Faruk, later | Nathan, separate user | Faruk and Nathan, separate | Unknown | Company vault, later | Account reported created. No project linked |
| Sentry | hawkvisionhomes@gmail.com | Same permanent mailbox | Faruk, later | Nathan | Faruk and Nathan, separate | Unknown | DSN injected later, not committed | GitHub integration reported. No DSN supplied |

Ann does not receive infrastructure, billing, secret, database-console, deployment-console, or development permissions.

Before production: move ownership to a HawkVision domain mailbox, give Faruk and Nathan separate named administrator accounts, verify MFA and recovery methods, and store secrets in the company vault. Shared day-to-day passwords are prohibited.

Offboarding removes the person from each provider, rotates secrets they could access, and records the rotation without copying secret values into git or chat.

Access review cadence before production is at least quarterly. Break-glass access is a named, expiring, attributable exception approved by Faruk for business impact and Nathan for the technical change. It is not a shared password.

# Scope, approved decisions, open decisions and assumptions

## Scope approved for this iteration
Preserve the premium charcoal/copper/typographic/Cincinnati direction. Refine public contrast, responsive composition, grammar and residential/commercial distinctions. Establish executable schemas, synthetic scenarios, read-only role shells, policy simulations and repository contracts. Retain public navigation: Available Rentals, Properties, How to Apply, Resident Resources, Maintenance, About, Contact HawkVision, Sign in to PerchPoint.

## Approved decisions
1. HawkVision Homes is a rental/property-operations company, not a buyer/seller brokerage.
2. PerchPoint is the operating platform. Public-facing “OS” is removed.
3. Canonical IDs are PerchPoint UUIDs. Provider identifiers cannot become primary keys.
4. One canonical organization/property/person graph underlies every role preview. No portal-specific databases or copies of canonical records.
5. Single-family, duplex, triplex, multifamily, commercial, mixed-use and multi-building sites are first-class.
6. Shared spaces describe locations; assets describe maintainable equipment/infrastructure. They are not artificial rentable units.
7. Individual identities are retained for adult signers and consent/notice attribution. Occupants do not automatically have accounts. No shared passwords.
8. Farouk has broad business authority but no automatic developer/infrastructure privileges. Nathan’s technical authority is distinct from business, development and emergency support purposes.
9. Final applicant approval, new leases and legal matters are owner-reserved.
10. Policy amounts are configurable examples pending Farouk, never a global $500 authorization rule.
11. Future production authorization requires server checks and tested PostgreSQL RLS; frontend gates are not security.
12. Innago and other tools are migration sources to archive and retire after cutover, not the intended permanent architecture.
13. No external messages, payments, screening, signing, uploads, real accounts or autonomous decisions in this iteration.
14. No automatic advancement into a later phase.

## Assumption register / open decisions
| ID | Assumption or decision needed | Owner | Consequence |
|---|---|---|---|
| A01 | Legal HawkVision entity and ownership/client relationships are unverified | Farouk | Example LLC/trust only |
| A02 | Real properties, addresses, unit terms, imagery, occupancy, dates, fees and pet/utility policies are not supplied | Farouk | Entire catalog synthetic |
| A03 | $250 staff / $500 parts / 1× monthly-rent examples are not approved | Farouk | Offline simulation only |
| A04 | Owner legal/applicant/lease authority delegated only after specific approval | Farouk/legal | Reserved by contract |
| A05 | Emergency authority duration, notification targets and retrospective timing remain unset | Farouk/security/legal | No real dispatch or alerting |
| A06 | Identity provider, MFA factors, session TTLs, reset/lockout and recovery settings unapproved | Farouk/Nathan/security | No production sign-in |
| A07 | Jurisdiction conflicts, disclosures, deposit/late-fee/notice/maintenance rules need qualified review | Qualified counsel | No universal Ohio rules |
| A08 | Retention periods, legal-hold administration, screening access and deletion eligibility unapproved | Qualified counsel | Durations null; no deletion execution |
| A09 | Provider choice, capabilities, credential ownership, webhook semantics and cutover controls unapproved | Farouk/Nathan | All ten adapter types disconnected |
| A10 | PostgreSQL transition, transaction boundaries, row-level policies and audit store need design review | Nathan/Cursor | Mongo remains synthetic capture only |
| A11 | US/USD/square feet are fixture choices, not global jurisdiction defaults | Farouk | Other countries/currencies need approved display/localization contracts |

## Account/service ownership
Use company-controlled accounts, company technical mailbox and Farouk as recovery owner. Named administrators only; role-based invitations, password-manager storage, HawkVision-controlled MFA recovery, and company-card billing only when approved. Never hand over a shared master password or approval code. No subscriptions or production credentials requested here.
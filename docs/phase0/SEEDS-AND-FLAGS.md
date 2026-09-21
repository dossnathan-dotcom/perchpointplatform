# Seed catalog and configuration behavior

All data is synthetic, including addresses, ownership entities, applicants, account references, portfolio terms, assignments and policies. Cincinnati imagery is illustrative, **not verified photographs of these invented units**. Farouk/Nathan are approved role labels, not invented biographies. No testimonials, history claims, performance statistics, real financial credentials, raw screening information or verified availability are introduced.

## Canonical seed catalog
One synthetic HawkVision organization, two explicitly fictional ownership entities (including a third-party client trust), six properties, seven buildings, fifteen units, thirty-five shared-space records and twenty-one assets.

| Property scenario | Shape |
|---|---|
| Example Garden House | One building / one residential unit |
| Example Clifton Duplex | One building / two residential units |
| Example Heritage Triplex | Three units, occupied and available examples |
| Example Elm Court | Two residential units + occupied fictional bakery C1 in the same building |
| Example Commerce Site | Commercial-only, two commercial units, Kentucky |
| Example River Campus | Multifamily, two buildings, Pennsylvania, third-party ownership |

People: nine explicitly named examples, seven **synthetic account references** (not real accounts), two households, one fictional business tenant, multiple temporal relationships. Primary household holder and adult co-signer have individual references; minor and emergency contact have no accounts. Applicant household has two adults plus guarantor. A person can have a former resident or staff/contact relationship without duplicate identity.

Eight role shells include owner/admin access, leasing portfolio visibility, restricted accounting, assigned maintenance, one subcontractor assignment, resident and applicant contexts. Delegation scenarios cover below threshold, above authority, expired delegation and emergency exception. Sensitive document denial and all role-access simulations are generated from policy functions. Payments/screening (and all other providers) are disconnected. Migration includes duplicate, invalid and conflicting rows.

## Flags (required explicit values)
| Environment | Flag | Preview value |
|---|---|---|
| Frontend | `REACT_APP_SHOW_DEMO_LABELS` | `true` |
| Frontend | `REACT_APP_ENABLE_SEEDED_PREVIEWS` | `true` |
| Backend | `PHASE0_ENABLED` | `true` |

`phase0Flags` rejects missing/nonboolean frontend configuration. The frontend computes `seedsEnabled = requestedPreviews && showLabels`. **Turning labels off also removes seeded inventory, hierarchy and workspace/review surfaces**; unverified data cannot quietly become “real” inventory. Empty verified-public states remain. Disabled flags do not activate production auth or operations.
The backend independently returns empty public catalogs, 404 on foundation previews and 503 on intake when `PHASE0_ENABLED=false`. Align both sides before production. These are release flags, not authorization controls.
CRA embeds frontend flags at build/start time. Change values and restart/rebuild using the normal service workflow. There is deliberately no public browser override to remove seed disclosures. Protected URL/database environment keys must remain unchanged; no provider credentials are added.

## Preview entry
`/perchpoint` → choose role → “Enter seeded workspace”. No email/password is needed. Role navigation uses `/perchpoint/{role}/{view}` and survives refresh. Search filters synthetic rows; property context filters portfolio-capable views. Notification/account menus work but show no real alerts/session. State selector exposes meaningful empty/loading/error/denied states. Row details open a seeded modal; execution controls are disabled.
`/foundation` offers the versioned review surface. The account/role selectors never create a backend account or authority.

Synthetic inquiry forms accept fictional data with example.com/example.org/example.net email domains and persist **only existing demo capture records** to MongoDB. They neither message anyone nor schedule/dispatch/submit an application. Free text is still user input: do not enter real personal data. Automatic PII detection is not implemented.
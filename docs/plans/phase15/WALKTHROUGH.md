# Phase 15 synthetic walkthrough

This walkthrough uses fictional example identities already in the local seed. It is not stakeholder acceptance and it does not use real residents, leases, or provider accounts.

| Persona | Starting route | Problem | Action | Expected result | Boundary |
| --- | --- | --- | --- | --- | --- |
| Owner analogue `faruk.synthetic@example.com` | `/portal` | Staff need one place to explain household access | Review the household hub and configuration warnings | The page shows a sample lease marker and demo previews | No production identity or legal copy is published |
| Operations analogue `ann.synthetic@example.com` | `/api/v2/leasing/portal/memberships` | A resident needs access after move-in | Open a portal only from an activated lease | A pending membership and one-time invitation capability are returned | Activation history is not rewritten |
| Primary resident | `/public/portal/invitations` | The resident must accept the exact invitation | Submit the capability once | The membership becomes active and a replay does not create another | A forwarded or forged token does not bind a different person |
| Co-resident and invited member | Household hub | More than one adult may need access | Show role labels without shared private requests | Leaseholder and co-resident stay separate | A household id is not authority |
| Accessibility preference | Preferences command | A resident needs a quieter channel | Save a new preference version | Version 1 is stored and does not change the lease | Interface preference is not an accommodation decision |
| Pending profile request | Requests command | A display name may be wrong | Submit a profile request | The request is recorded and the lease stays activated | Canonical tenancy is not edited |
| Sample lease | Documents command | The household needs the package | Download the entitled artifact | The sample marker is present and the response is `no-store` | The file is not a real or approved lease |
| Later destinations | Home command | People ask where money, repairs, and messages will live | Read the demo preview list | Each item is labeled non-authoritative | No balance, payment, work order, or delivery is created |
| Revoked membership | Revocations command | Access must stop | Revoke the membership | A later download is rejected | Revocation does not delete the audit history |
| Empty and isolated states | Another organization | Same names must not leak | Sign in as `isolation.synthetic@example.com` | The household is denied | Demo data does not weaken row security |

Reset check: `python scripts/phase15_demo.py --verify`. It refuses a non-local target. Real organization facts stay in the activation manifest until a later governed batch.

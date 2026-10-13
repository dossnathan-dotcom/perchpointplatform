# Phase 20 authorization

Server capabilities and row security decide access. A hidden button does not.

| Action | Capability | Who |
| --- | --- | --- |
| Report a problem | `maintenance.report` | Resident, household adult, worker, coordinator, owner |
| Read one's own report | `maintenance.report` and reporter or resident match | The household that reported it |
| Queue, review, decide, notice | `maintenance.coordinate` | Ann and Faruk |
| Accept work, time, evidence, location | `work.assign` | The assigned worker |
| Authorize spending | `purchase.authorize` | Ann within $1,200, Faruk for owner-reserved amounts |

Workers do not receive `purchase.authorize`. A technician who calls the decision
route is denied. Related decision amounts on one case are added together, so the
$1,200 limit cannot be split. The $2,500 emergency path is stored as provisional.

Access instructions are readable by a coordinator or the worker who has accepted
the assignment. Location coordinates are readable by the worker who recorded them.
The coordinator sees the outcome without the coordinates. Internal notes are not
returned on the resident projection.

The reviewer of a completion cannot be the person who submitted it. A worker
cannot approve their own exceptional time correction.

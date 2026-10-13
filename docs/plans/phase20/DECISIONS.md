# Phase 20 decisions

These decisions record Nathan's assignment for repository Phase 20. They do not
rewrite the roadmap PDF. See CONFLICT-028. `real_values_activated` and
`money_moved` stay false.

## Q01 — Principal demo

The demo shows the mismatch between what a worker needs and what Ann or Faruk
provides, plus the miscommunication around that handoff. Recommendations, exact
specifications, substitutions, acknowledgments, blockers, responsible people,
lost time, and outcomes stay distinct.

## Q02 — Who can report

An authenticated resident can report. Staff can record a call, text, email, or
in-person report. An authorized worker can report a unit, vacant home, or common
area. The original reporter, the person who entered it, the source, the reported
time, and the server receipt time are all kept. Live telephony remains Phase 21.
There is one case system: `maintenance_cases`.

## Q03 — Urgency

The short questions are immediate danger, continuing damage, essential services,
affected area, and worsening. A resident may flag an emergency. A staff change
needs a person and a reason. Automation may suggest or raise severity. It cannot
quietly downgrade a human emergency flag. Missing photos never block a report or
an emergency escalation.

## Q04 — Who owns the response

Ann owns ordinary triage. If the primary person does not acknowledge, the path
continues to the backup and then to Faruk. A delivered notification is not
accepted responsibility. Schedules and contacts in this phase are synthetic.
This phase does not claim real 24/7 coverage.

## Q05 — Separate clocks

Acknowledgment, assessment, arranging service, the next update, and repair
completion are separate. Demo acknowledgment targets are 5 minutes for an
emergency, 1 hour for urgent, and one business day (1,440 minutes) for routine.
Those are configurable operating targets, not a legal promise. Emergency timing
is continuous. Inspection deadlines are not reset by ordinary routing.

## Q06 — Access

Presence, availability, pets, obstacles, communication needs, and request-specific
entry instructions stay on the request. One request is not permission to enter
every time. Instructions are readable by the current assignee and coordinators.
Photos, unpaid rent, or a balance dispute cannot block intake.

## Q07 — What the worker records

The worker records the job, the observed condition, the exact need, a
recommendation, safety, tools and materials, equipment identifiers, the next
action, time, and before-and-after evidence. The recommendation stays distinct
from the action management chooses. The worker surface is a phone-width web page.

## Q08 — Duplicates

The product can suggest a link. A person confirms it. Every report is kept. A
shared incident is not the same thing as a repeat failure. Linking does not erase
the first report time, reset a deadline, or show one household's private notes
to another.

## Q09 — What a resident sees

The resident sees receipt, a public status, the responsible team, the last
meaningful update, the next expected update, and a way to add information or
report worsening. Status words are received, reviewed, responsibility accepted,
visit planned, and work completed. The product does not say someone is on the
way unless a visit is actually planned. Internal notes, time disputes, purchasing
disagreements, and access instructions stay hidden.

## Q10 — What Faruk sees

The owner briefing shows unacknowledged emergencies, serious safety items,
missed deadlines, decisions reserved to him, and jobs blocked by a material or
instruction mismatch. Each item has the property, urgency, owner, next action,
and age, and it links to the same records Ann uses. Routine volume stays in the
queue rather than inventing a second count.

## Q11 — Spending authority

Ann may authorize routine work up to and including $1,200 (120,000 minor units)
when policy permits. Capital work, a higher aggregate, and owner-reserved matters
go to Faruk. Related decisions on one case are added together. Workers have no
purchasing authority. A provisional emergency allowance of $2,500 (250,000 minor
units) is marked provisional, with owner notice and a required later review.
This phase records the decision. It does not move money or pay a vendor.

## Q12 — Inspection notices

A notice keeps the program, the source, the cited deficiency, the home or common
area, the owner, the deadline, and the deadline version. The deadline is not a
hard-coded generic HUD date. The notice does not post a resident charge, withhold
assistance, or change a balance.

## Q13 — Handoff and closure

A named person accepts the current scope, urgency, evidence, access, and next
action. Triage complete is not repair complete. The technician submits evidence.
A different authorized reviewer verifies it. Silence, an elapsed timer,
reassignment, or a successful notification does not complete the repair.

## Smaller defaults

Readable case numbers are shown. Stable identifiers stay internal. The minimum
report is a place, a description, and an urgency answer. Places are a unit, a
building, a common area, or a vacant home. One coordinator is accountable.
A transfer is proposed, then accepted or declined with a reason. A new material
revision needs a new acknowledgment. A blocker names a resolver and a next update.
Materials can record quantity, unit, manufacturer, model, dimensions,
alternatives, and unknowns. Partial delivery shows received and remaining.
Photos have a stage. Time categories are diagnosis, on-site, travel, materials
pickup, waiting, and administration. They are not wages. The property zone is
America/New_York. Estimated cost is an operational record only. Location
coordinates are stored apart from the long-lived audit row, and only after an
explicit check-in.

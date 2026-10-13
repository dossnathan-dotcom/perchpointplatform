# Phase 20 workflows

1. A resident, staff member, or worker submits a place, a description, and urgency.
   The server stores the reporter, the person who entered it, the reported time,
   and the receipt time. An emergency returns the safety message immediately.
2. An emergency queues an escalation. The separate `python -m perchpoint.phase20_worker`
   process claims one row. A failed delivery queues the next step. Delivered mail
   is not accepted responsibility. Quiet hours do not suppress the emergency path.
3. Ann reviews the queue. Review marks the case reviewed and acknowledges the
   queued escalation. Responsibility stays with Ann until a named person accepts.
4. The worker records an exact need. Ann or Faruk records a decision against that
   revision. A later revision cannot reuse the older acknowledgment. A worker
   cannot authorize the purchase.
5. Arrival is recorded as received, remaining, used, and returned. The worker
   records whether it matches. A mismatch opens a blocker with a resolver and a
   next update. Remaining quantity cannot show the need as ready.
6. The worker starts and stops time. A second open interval for the same worker
   is refused. Stopping time does not require a photo or a location.
7. Location is a separate check-in. Denied, timed out, inaccurate, or unavailable
   results stay honest. Raw coordinates are not written into the case timeline.
8. Ordinary completion needs a before photo and an after photo. A safety, access,
   privacy, or upload exception is visible and is not treated as verified.
9. A different coordinator verifies, asks for clarification, or reopens the work.
   Resident silence does not close the case.
10. Faruk's briefing reads the same cases as Ann's queue.

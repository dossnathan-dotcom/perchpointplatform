-- Phase 20 extends maintenance_cases. It does not open a second maintenance system or move money.

SET LOCAL ROLE perchpoint_definer;
INSERT INTO capabilities (code, family, description)
VALUES ('maintenance.report', 'maintenance', 'Report a maintenance problem')
ON CONFLICT (code) DO NOTHING;

INSERT INTO role_bundle_capabilities (bundle_id, capability)
SELECT bundle.id, 'maintenance.report'
FROM role_bundles bundle
WHERE bundle.name IN (
  'resident', 'household_adult', 'technician', 'cleaner', 'maintenance',
  'maintenance_coordinator', 'operations_manager', 'owner', 'project_manager'
)
ON CONFLICT DO NOTHING;
RESET ROLE;

CREATE POLICY maintenance_case_report_insert ON maintenance_cases
  FOR INSERT
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND created_by = perchpoint.current_actor()
    AND perchpoint.has_capability('maintenance.report')
  );

CREATE POLICY maintenance_case_report_read ON maintenance_cases
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND created_by = perchpoint.current_actor()
    AND perchpoint.has_capability('maintenance.report')
  );

CREATE TABLE maintenance_reports (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  reporter_actor uuid NOT NULL,
  resident_actor uuid,
  entered_by uuid NOT NULL,
  source text NOT NULL CHECK (source IN ('resident', 'phone', 'text', 'email', 'in_person', 'worker')),
  reported_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  place_kind text NOT NULL CHECK (place_kind IN ('unit', 'building', 'common_area', 'vacant_home')),
  place_label text NOT NULL,
  household_label text,
  description text NOT NULL,
  urgency jsonb NOT NULL,
  human_emergency boolean NOT NULL DEFAULT false,
  severity text NOT NULL CHECK (severity IN ('emergency', 'urgent', 'routine')),
  rule_version integer NOT NULL DEFAULT 1,
  safety_message text,
  summary text NOT NULL CHECK (summary IN ('received', 'reviewed', 'accepted', 'visit_planned', 'completed', 'withdrawn')),
  coordinator_actor uuid,
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  ack_due_at timestamptz NOT NULL,
  next_update_at timestamptz,
  linked_case_id uuid,
  worsening boolean NOT NULL DEFAULT false,
  environment text NOT NULL CHECK (environment = 'local_fake'),
  money_moved boolean NOT NULL CHECK (money_moved = false),
  real_values_activated boolean NOT NULL CHECK (real_values_activated = false),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES maintenance_cases (organization_id, id)
);

CREATE TABLE maintenance_access (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  instructions text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES maintenance_cases (organization_id, id)
);

CREATE TABLE maintenance_assignments (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  assignee_actor uuid NOT NULL,
  state text NOT NULL CHECK (state IN ('proposed', 'accepted', 'declined')),
  reason text,
  version integer NOT NULL DEFAULT 1,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES maintenance_cases (organization_id, id)
);

CREATE UNIQUE INDEX maintenance_one_accepted_assignment
  ON maintenance_assignments (organization_id, case_id)
  WHERE state = 'accepted';

CREATE TABLE maintenance_needs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  revision integer NOT NULL CHECK (revision > 0),
  author_actor uuid NOT NULL,
  specification text NOT NULL,
  quantity numeric NOT NULL CHECK (quantity > 0),
  unit_name text NOT NULL,
  manufacturer text,
  model_number text,
  dimensions text,
  alternatives text,
  unknowns text,
  amount_minor integer CHECK (amount_minor IS NULL OR amount_minor >= 0),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, case_id, revision),
  FOREIGN KEY (organization_id, case_id) REFERENCES maintenance_cases (organization_id, id)
);

CREATE TABLE maintenance_decisions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  needs_revision integer NOT NULL,
  actor_id uuid NOT NULL,
  selected_specification text NOT NULL,
  reason text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  authority text NOT NULL CHECK (authority IN ('routine', 'emergency_provisional', 'owner')),
  provisional boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id) REFERENCES maintenance_cases (organization_id, id)
);

CREATE TABLE maintenance_fulfillment (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  decision_id uuid NOT NULL,
  quantity_received numeric NOT NULL CHECK (quantity_received >= 0),
  quantity_remaining numeric NOT NULL CHECK (quantity_remaining >= 0),
  quantity_used numeric NOT NULL DEFAULT 0 CHECK (quantity_used >= 0),
  quantity_returned numeric NOT NULL DEFAULT 0 CHECK (quantity_returned >= 0),
  condition text NOT NULL,
  reference_label text,
  actor_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_compatibility (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  needs_revision integer NOT NULL,
  result text NOT NULL CHECK (result IN ('accepted', 'partial', 'rejected')),
  mismatch text,
  actor_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_blockers (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  kind text NOT NULL,
  resolver_actor uuid NOT NULL,
  reason text NOT NULL,
  next_update_at timestamptz NOT NULL,
  state text NOT NULL CHECK (state IN ('open', 'resolved')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_visits (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  state text NOT NULL CHECK (state IN ('planned', 'submitted', 'verified', 'clarification', 'reopened')),
  exception_reason text,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_evidence (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  visit_id uuid NOT NULL,
  stage text NOT NULL CHECK (stage IN ('before', 'after', 'arrival', 'departure')),
  caption text NOT NULL,
  content_sha text NOT NULL,
  scan_state text NOT NULL CHECK (scan_state IN ('pending', 'available', 'rejected')),
  uploader_actor uuid NOT NULL,
  captured_at timestamptz,
  uploaded_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_time_intervals (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  category text NOT NULL CHECK (category IN ('diagnosis', 'on_site', 'travel', 'materials_pickup', 'waiting', 'administration')),
  started_at timestamptz NOT NULL,
  ended_at timestamptz,
  server_started_at timestamptz NOT NULL DEFAULT now(),
  server_ended_at timestamptz,
  source text NOT NULL CHECK (source IN ('timer', 'manual')),
  description text,
  overlap_flag boolean NOT NULL DEFAULT false,
  version integer NOT NULL DEFAULT 1,
  PRIMARY KEY (organization_id, id)
);

CREATE UNIQUE INDEX maintenance_one_open_interval
  ON maintenance_time_intervals (organization_id, actor_id)
  WHERE ended_at IS NULL;

CREATE TABLE maintenance_time_adjustments (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  interval_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  reason text NOT NULL,
  reviewer_actor uuid,
  state text NOT NULL CHECK (state IN ('proposed', 'approved', 'rejected')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  CHECK (reviewer_actor IS NULL OR reviewer_actor <> actor_id)
);

CREATE TABLE maintenance_locations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  latitude numeric,
  longitude numeric,
  accuracy_meters numeric,
  outcome text NOT NULL CHECK (outcome IN ('synthetic', 'denied', 'timeout', 'inaccurate', 'unavailable', 'unsupported')),
  observed_at timestamptz NOT NULL,
  received_at timestamptz NOT NULL DEFAULT now(),
  deleted_at timestamptz,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_location_audit (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  outcome text NOT NULL,
  observed_at timestamptz NOT NULL,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_notes (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  visibility text NOT NULL CHECK (visibility IN ('resident', 'internal')),
  body text NOT NULL,
  worsening boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_notices (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  program text NOT NULL,
  source_label text NOT NULL,
  deficiency text NOT NULL,
  deadline_at timestamptz NOT NULL,
  deadline_version integer NOT NULL,
  owner_actor uuid NOT NULL,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE maintenance_escalations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  step integer NOT NULL CHECK (step >= 0),
  recipient_role text NOT NULL,
  state text NOT NULL CHECK (state IN ('queued', 'attempted', 'delivered', 'failed', 'acknowledged', 'unresolved')),
  human_acknowledged boolean NOT NULL DEFAULT false,
  fail_delivery boolean NOT NULL DEFAULT false,
  dedup_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, dedup_key)
);

CREATE TABLE maintenance_reviews (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  visit_id uuid NOT NULL,
  submitter_actor uuid NOT NULL,
  reviewer_actor uuid NOT NULL,
  outcome text NOT NULL CHECK (outcome IN ('verified', 'clarification', 'reopened')),
  reason text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  CHECK (reviewer_actor <> submitter_actor)
);

CREATE TABLE maintenance_commands (
  organization_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, actor_id, idempotency_key)
);

ALTER TABLE maintenance_reports ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_reports FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_access ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_access FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_assignments FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_needs ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_needs FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_decisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_decisions FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_fulfillment ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_fulfillment FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_compatibility ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_compatibility FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_blockers ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_blockers FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_visits ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_visits FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_evidence ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_evidence FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_time_intervals ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_time_intervals FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_time_adjustments ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_time_adjustments FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_locations FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_location_audit ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_location_audit FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_notes FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_notices FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_escalations ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_escalations FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_reviews FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_commands FORCE ROW LEVEL SECURITY;

CREATE POLICY maintenance_reports_scope ON maintenance_reports
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR (perchpoint.has_capability('maintenance.report') AND (
        reporter_actor = perchpoint.current_actor() OR resident_actor = perchpoint.current_actor()
      ))
      OR (perchpoint.has_capability('work.assign') AND EXISTS (
        SELECT 1 FROM maintenance_assignments assignment
        WHERE assignment.organization_id = maintenance_reports.organization_id
          AND assignment.case_id = maintenance_reports.case_id
          AND assignment.assignee_actor = perchpoint.current_actor()
          AND assignment.state IN ('proposed', 'accepted')
      ))
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR (perchpoint.has_capability('maintenance.report') AND reporter_actor = perchpoint.current_actor())
      OR (perchpoint.has_capability('work.assign') AND EXISTS (
        SELECT 1 FROM maintenance_assignments assignment
        WHERE assignment.organization_id = maintenance_reports.organization_id
          AND assignment.case_id = maintenance_reports.case_id
          AND assignment.assignee_actor = perchpoint.current_actor()
          AND assignment.state IN ('proposed', 'accepted')
      ))
    )
  );

CREATE POLICY maintenance_access_scope ON maintenance_access
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR (perchpoint.has_capability('work.assign') AND EXISTS (
        SELECT 1 FROM maintenance_assignments assignment
        WHERE assignment.organization_id = maintenance_access.organization_id
          AND assignment.case_id = maintenance_access.case_id
          AND assignment.assignee_actor = perchpoint.current_actor()
          AND assignment.state = 'accepted'
      ))
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('maintenance.coordinate')
  );

CREATE POLICY maintenance_assignments_scope ON maintenance_assignments
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR (perchpoint.has_capability('work.assign') AND assignee_actor = perchpoint.current_actor())
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR (perchpoint.has_capability('work.assign') AND assignee_actor = perchpoint.current_actor())
    )
  );

CREATE POLICY maintenance_needs_scope ON maintenance_needs
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR (perchpoint.has_capability('work.assign') AND EXISTS (
        SELECT 1 FROM maintenance_assignments assignment
        WHERE assignment.organization_id = maintenance_needs.organization_id
          AND assignment.case_id = maintenance_needs.case_id
          AND assignment.assignee_actor = perchpoint.current_actor()
          AND assignment.state = 'accepted'
      ))
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR (perchpoint.has_capability('work.assign') AND author_actor = perchpoint.current_actor() AND EXISTS (
        SELECT 1 FROM maintenance_assignments assignment
        WHERE assignment.organization_id = maintenance_needs.organization_id
          AND assignment.case_id = maintenance_needs.case_id
          AND assignment.assignee_actor = perchpoint.current_actor()
          AND assignment.state = 'accepted'
      ))
    )
  );

CREATE POLICY maintenance_decisions_scope ON maintenance_decisions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('maintenance.coordinate'))
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('purchase.authorize')
    AND actor_id = perchpoint.current_actor()
  );

CREATE POLICY maintenance_worker_read_scope ON maintenance_fulfillment
  USING (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR perchpoint.has_capability('work.assign')))
  WITH CHECK (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR perchpoint.has_capability('work.assign')));

CREATE POLICY maintenance_compatibility_scope ON maintenance_compatibility
  USING (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR perchpoint.has_capability('work.assign')))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('work.assign') AND actor_id = perchpoint.current_actor());

CREATE POLICY maintenance_blockers_scope ON maintenance_blockers
  USING (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR perchpoint.has_capability('work.assign')))
  WITH CHECK (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR perchpoint.has_capability('work.assign')));

CREATE POLICY maintenance_visits_scope ON maintenance_visits
  USING (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR perchpoint.has_capability('work.assign')))
  WITH CHECK (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR (perchpoint.has_capability('work.assign') AND actor_id = perchpoint.current_actor())));

CREATE POLICY maintenance_evidence_scope ON maintenance_evidence
  USING (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR perchpoint.has_capability('work.assign') OR (perchpoint.has_capability('maintenance.report') AND uploader_actor = perchpoint.current_actor())))
  WITH CHECK (organization_id = perchpoint.current_org() AND uploader_actor = perchpoint.current_actor() AND (perchpoint.has_capability('work.assign') OR perchpoint.has_capability('maintenance.report')));

CREATE POLICY maintenance_time_scope ON maintenance_time_intervals
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR (perchpoint.has_capability('work.assign') AND actor_id = perchpoint.current_actor())
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      (perchpoint.has_capability('work.assign') AND actor_id = perchpoint.current_actor())
      OR perchpoint.has_capability('maintenance.coordinate')
    )
  );

CREATE POLICY maintenance_time_adjustment_scope ON maintenance_time_adjustments
  USING (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR actor_id = perchpoint.current_actor()))
  WITH CHECK (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('maintenance.coordinate') OR actor_id = perchpoint.current_actor()));

CREATE POLICY maintenance_locations_scope ON maintenance_locations
  USING (organization_id = perchpoint.current_org() AND actor_id = perchpoint.current_actor() AND deleted_at IS NULL)
  WITH CHECK (organization_id = perchpoint.current_org() AND actor_id = perchpoint.current_actor() AND perchpoint.has_capability('work.assign'));

CREATE POLICY maintenance_location_audit_scope ON maintenance_location_audit
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('maintenance.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('work.assign'));

CREATE POLICY maintenance_notes_scope ON maintenance_notes
  USING (
    organization_id = perchpoint.current_org() AND (
      (visibility = 'resident' AND (
        perchpoint.has_capability('maintenance.coordinate')
        OR actor_id = perchpoint.current_actor()
        OR EXISTS (
          SELECT 1 FROM maintenance_reports report
          WHERE report.organization_id = maintenance_notes.organization_id
            AND report.case_id = maintenance_notes.case_id
            AND (report.reporter_actor = perchpoint.current_actor() OR report.resident_actor = perchpoint.current_actor())
        )
      ))
      OR (visibility = 'internal' AND (
        perchpoint.has_capability('maintenance.coordinate')
        OR (perchpoint.has_capability('work.assign') AND EXISTS (
          SELECT 1 FROM maintenance_assignments assignment
          WHERE assignment.organization_id = maintenance_notes.organization_id
            AND assignment.case_id = maintenance_notes.case_id
            AND assignment.assignee_actor = perchpoint.current_actor()
            AND assignment.state = 'accepted'
        ))
      ))
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND actor_id = perchpoint.current_actor()
    AND (
      visibility = 'resident'
      OR perchpoint.has_capability('maintenance.coordinate')
      OR (
        visibility = 'internal'
        AND perchpoint.has_capability('work.assign')
        AND EXISTS (
          SELECT 1 FROM maintenance_assignments assignment
          WHERE assignment.organization_id = maintenance_notes.organization_id
            AND assignment.case_id = maintenance_notes.case_id
            AND assignment.assignee_actor = perchpoint.current_actor()
            AND assignment.state = 'accepted'
        )
      )
    )
  );

CREATE POLICY maintenance_notices_scope ON maintenance_notices
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('maintenance.coordinate'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('maintenance.coordinate'));

CREATE POLICY maintenance_escalations_scope ON maintenance_escalations
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR perchpoint.has_capability('outbox.deliver')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('maintenance.coordinate')
      OR perchpoint.has_capability('maintenance.report')
      OR perchpoint.has_capability('outbox.deliver')
    )
  );

CREATE POLICY maintenance_reviews_scope ON maintenance_reviews
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('maintenance.coordinate'))
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('maintenance.coordinate')
    AND reviewer_actor = perchpoint.current_actor()
  );

CREATE POLICY maintenance_commands_scope ON maintenance_commands
  USING (organization_id = perchpoint.current_org() AND actor_id = perchpoint.current_actor())
  WITH CHECK (organization_id = perchpoint.current_org() AND actor_id = perchpoint.current_actor());

CREATE POLICY membership_maintenance_household_read ON memberships
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND role_name IN ('resident', 'household_adult')
    AND (ended_at IS NULL OR ended_at > now())
    AND perchpoint.has_capability('maintenance.coordinate')
  );

GRANT SELECT, INSERT, UPDATE ON
  maintenance_reports, maintenance_access, maintenance_assignments, maintenance_needs,
  maintenance_decisions, maintenance_fulfillment, maintenance_compatibility, maintenance_blockers,
  maintenance_visits, maintenance_evidence, maintenance_time_intervals, maintenance_time_adjustments,
  maintenance_locations, maintenance_notes, maintenance_notices, maintenance_escalations, maintenance_reviews
  TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON maintenance_location_audit, maintenance_commands TO perchpoint_runtime, perchpoint_definer;

CREATE POLICY membership_maintenance_coordinator_read ON memberships
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND role_name = 'operations_manager'
    AND (ended_at IS NULL OR ended_at > now())
    AND (
      perchpoint.has_capability('maintenance.report')
      OR perchpoint.has_capability('maintenance.coordinate')
      OR perchpoint.has_capability('work.assign')
    )
  );

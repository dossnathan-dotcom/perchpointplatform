CREATE TABLE maintenance_cases (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  assignment_id uuid,
  status text NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'completed', 'cancelled')),
  created_by uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, assignment_id)
    REFERENCES worker_assignments(organization_id, id)
);

CREATE TABLE maintenance_case_events (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  case_id uuid NOT NULL,
  event_type text NOT NULL CHECK (event_type IN (
    'reported_problem',
    'technician_observation',
    'technician_recommendation',
    'manager_decision',
    'approved_solution',
    'ordered_product',
    'installed_solution',
    'variance_reason'
  )),
  content text NOT NULL,
  actor_id uuid NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, case_id)
    REFERENCES maintenance_cases(organization_id, id)
);

ALTER TABLE maintenance_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_cases FORCE ROW LEVEL SECURITY;
ALTER TABLE maintenance_case_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE maintenance_case_events FORCE ROW LEVEL SECURITY;

CREATE POLICY maintenance_case_scope ON maintenance_cases
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND (
      perchpoint.current_role() IN (
        'owner', 'project_manager', 'operations_manager', 'maintenance_coordinator'
      )
      OR EXISTS (
        SELECT 1
        FROM worker_assignments assignment
        WHERE assignment.organization_id = maintenance_cases.organization_id
          AND assignment.id = maintenance_cases.assignment_id
          AND assignment.worker_account_id = perchpoint.current_actor()
          AND assignment.status = 'active'
          AND assignment.starts_at <= now()
          AND assignment.ends_at > now()
      )
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND created_by = perchpoint.current_actor()
    AND perchpoint.current_role() IN (
      'owner', 'project_manager', 'operations_manager', 'maintenance_coordinator'
    )
  );

CREATE POLICY maintenance_event_scope ON maintenance_case_events
  USING (
    organization_id = perchpoint.current_org()
    AND EXISTS (
      SELECT 1
      FROM maintenance_cases case_record
      WHERE case_record.organization_id = maintenance_case_events.organization_id
        AND case_record.id = maintenance_case_events.case_id
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND actor_id = perchpoint.current_actor()
    AND EXISTS (
      SELECT 1
      FROM maintenance_cases case_record
      WHERE case_record.organization_id = maintenance_case_events.organization_id
        AND case_record.id = maintenance_case_events.case_id
    )
  );

GRANT SELECT, INSERT, UPDATE ON maintenance_cases TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON maintenance_case_events TO perchpoint_runtime, perchpoint_definer;
REVOKE UPDATE, DELETE ON maintenance_case_events FROM perchpoint_runtime;

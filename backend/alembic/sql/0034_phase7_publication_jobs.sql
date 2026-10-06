-- Phase 7 scheduled publication jobs. Execution rechecks authority; history stays append-only.

ALTER TABLE content_items
  ADD COLUMN scheduled_for timestamptz,
  ADD COLUMN schedule_zone text;

CREATE TABLE content_jobs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  item_id uuid NOT NULL,
  action text NOT NULL CHECK (action IN ('publish', 'expire')),
  run_at timestamptz NOT NULL,
  time_zone text NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'succeeded', 'failed')),
  attempts integer NOT NULL DEFAULT 0,
  last_error text,
  initiator_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  finished_at timestamptz,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, item_id) REFERENCES content_items (organization_id, id)
);

ALTER TABLE content_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_jobs FORCE ROW LEVEL SECURITY;

CREATE POLICY content_jobs_staff ON content_jobs
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.schedule'));

GRANT SELECT, INSERT, UPDATE ON content_jobs TO perchpoint_runtime, perchpoint_definer;
REVOKE DELETE ON content_jobs FROM perchpoint_runtime;

ALTER TABLE listings ADD COLUMN IF NOT EXISTS version integer NOT NULL DEFAULT 1 CHECK (version >= 1);

CREATE TABLE IF NOT EXISTS inquiry_notes (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  inquiry_id uuid NOT NULL REFERENCES inquiries(id),
  body text NOT NULL CHECK (char_length(body) BETWEEN 1 AND 2000),
  created_at timestamptz NOT NULL,
  actor_id uuid NOT NULL
);

ALTER TABLE inquiry_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE inquiry_notes FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_all ON inquiry_notes;
CREATE POLICY tenant_all ON inquiry_notes
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(organization_id))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(organization_id));

GRANT SELECT, INSERT ON inquiry_notes TO perchpoint_runtime;

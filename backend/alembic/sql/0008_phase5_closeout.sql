ALTER TABLE documents DROP CONSTRAINT documents_lifecycle_check;
ALTER TABLE documents ADD CONSTRAINT documents_lifecycle_check
  CHECK (lifecycle IN ('staged', 'scanning', 'available', 'quarantined', 'held', 'rejected', 'disposed'));
ALTER TABLE documents ADD COLUMN published boolean NOT NULL DEFAULT false;

ALTER TABLE saved_searches ADD COLUMN name text NOT NULL DEFAULT 'Saved search';
ALTER TABLE saved_searches ADD COLUMN visibility text NOT NULL DEFAULT 'private';
ALTER TABLE saved_searches ADD CONSTRAINT saved_searches_visibility_check
  CHECK (visibility IN ('private', 'organization'));
ALTER TABLE saved_searches ADD CONSTRAINT saved_searches_name_check
  CHECK (char_length(name) BETWEEN 1 AND 120);

DROP POLICY tenant_all ON saved_searches;
CREATE POLICY saved_search_read ON saved_searches
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND (actor_id = perchpoint.current_actor() OR visibility = 'organization')
  );
CREATE POLICY saved_search_write ON saved_searches
  FOR ALL
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND actor_id = perchpoint.current_actor()
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND actor_id = perchpoint.current_actor()
  );

ALTER TABLE import_batches DROP CONSTRAINT import_batches_status_check;
ALTER TABLE import_batches ADD CONSTRAINT import_batches_status_check
  CHECK (status IN ('staged', 'dry_run', 'approved', 'applied', 'rejected', 'rolled_back'));
ALTER TABLE import_batches ADD COLUMN mapping_version integer NOT NULL DEFAULT 1 CHECK (mapping_version >= 1);
ALTER TABLE import_batches ADD COLUMN approved_by uuid;

ALTER TABLE quality_findings ADD COLUMN assigned_to uuid;
ALTER TABLE quality_findings ADD COLUMN source_evidence text NOT NULL DEFAULT '';

CREATE TABLE document_jobs (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  correlation_id uuid NOT NULL,
  job_kind text NOT NULL CHECK (job_kind IN ('scan', 'extract', 'preview', 'index')),
  object_key text,
  status text NOT NULL CHECK (status IN ('pending', 'leased', 'done', 'dead')),
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  lease_until timestamptz,
  available_at timestamptz NOT NULL DEFAULT now(),
  last_error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (organization_id, document_id) REFERENCES documents (organization_id, id)
);

CREATE INDEX document_jobs_ready ON document_jobs (status, available_at);

CREATE TABLE document_artifacts (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL,
  version_id uuid NOT NULL,
  artifact_kind text NOT NULL CHECK (artifact_kind IN ('ocr', 'preview')),
  object_key text,
  page_number integer CHECK (page_number IS NULL OR page_number >= 1),
  engine text NOT NULL,
  engine_version text NOT NULL,
  status text NOT NULL CHECK (status IN ('ready', 'failed', 'unsupported')),
  machine_generated boolean NOT NULL DEFAULT true CHECK (machine_generated),
  extracted_text text NOT NULL DEFAULT '',
  error text,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (organization_id, document_id) REFERENCES documents (organization_id, id)
);

CREATE TABLE document_access (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  token_hash text NOT NULL UNIQUE,
  purpose text NOT NULL CHECK (purpose IN ('download', 'preview', 'export')),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  FOREIGN KEY (organization_id, document_id) REFERENCES documents (organization_id, id)
);

CREATE TABLE document_exports (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL,
  scope jsonb NOT NULL,
  manifest jsonb NOT NULL,
  object_key text NOT NULL,
  status text NOT NULL CHECK (status IN ('ready', 'expired', 'failed')),
  expires_at timestamptz NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE replay_runs (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL,
  status text NOT NULL CHECK (status IN ('reconciled', 'dead')),
  expected_count integer NOT NULL CHECK (expected_count >= 0),
  actual_count integer NOT NULL CHECK (actual_count >= 0),
  detail text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE import_effects (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  batch_id uuid NOT NULL,
  party_id uuid NOT NULL,
  FOREIGN KEY (organization_id, batch_id) REFERENCES import_batches (organization_id, id)
);

DO $$
DECLARE tbl text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'document_jobs','document_artifacts','document_access','document_exports','replay_runs','import_effects'
  ]
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', tbl);
    EXECUTE format('ALTER TABLE %I FORCE ROW LEVEL SECURITY', tbl);
    EXECUTE format(
      'CREATE POLICY tenant_all ON %I USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(organization_id)) WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(organization_id))',
      tbl
    );
  END LOOP;
END $$;

GRANT SELECT, INSERT, UPDATE, DELETE ON
  document_jobs, document_artifacts, document_exports, import_effects, quality_findings
TO perchpoint_runtime;
GRANT SELECT, INSERT ON document_access, replay_runs TO perchpoint_runtime;

CREATE OR REPLACE FUNCTION perchpoint.claim_document_job(worker text)
RETURNS TABLE (organization_id uuid, actor_id uuid, job_id uuid, document_id uuid, job_kind text)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp AS $$
DECLARE claimed document_jobs%ROWTYPE;
BEGIN
  SELECT * INTO claimed FROM document_jobs
  WHERE status IN ('pending', 'leased')
    AND available_at <= now()
    AND (lease_until IS NULL OR lease_until < now())
  ORDER BY created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN
    RETURN;
  END IF;
  UPDATE document_jobs
    SET status = 'leased', lease_until = now() + interval '60 seconds', attempts = document_jobs.attempts + 1
    WHERE id = claimed.id;
  RETURN QUERY SELECT claimed.organization_id, claimed.actor_id, claimed.id, claimed.document_id, claimed.job_kind;
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.claim_document_job(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.claim_document_job(text) TO perchpoint_runtime;
ALTER FUNCTION perchpoint.claim_document_job(text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.actor_in_org(uuid) COST 10000;
GRANT SELECT, INSERT, UPDATE, DELETE ON
  document_jobs, document_artifacts, document_exports, import_effects, document_access, replay_runs
TO perchpoint_definer;



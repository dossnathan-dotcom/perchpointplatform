-- Phase 5 canonical records, documents, search, and import staging.
-- Alembic remains the only migration authority. Runtime audit privileges stay insert-only.

CREATE EXTENSION IF NOT EXISTS btree_gist;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

ALTER TABLE spaces DROP CONSTRAINT IF EXISTS spaces_use_check;
ALTER TABLE spaces ADD CONSTRAINT spaces_use_check CHECK (
  use IN ('residential', 'commercial', 'parking', 'storage', 'common', 'mechanical', 'other')
);

CREATE TABLE parties (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  party_kind text NOT NULL CHECK (party_kind IN ('person', 'household', 'legal_entity', 'vendor', 'employer', 'government', 'internal')),
  display_name text NOT NULL CHECK (char_length(display_name) BETWEEN 1 AND 200),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (id)
);

CREATE TABLE party_relationships (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  subject_party_id uuid NOT NULL,
  object_party_id uuid NOT NULL,
  relationship_kind text NOT NULL CHECK (char_length(relationship_kind) BETWEEN 1 AND 80),
  exclusive boolean NOT NULL DEFAULT false,
  effective_at timestamptz NOT NULL,
  ended_at timestamptz,
  CHECK (ended_at IS NULL OR ended_at > effective_at),
  CHECK (subject_party_id <> object_party_id),
  FOREIGN KEY (organization_id, subject_party_id) REFERENCES parties (organization_id, id),
  FOREIGN KEY (organization_id, object_party_id) REFERENCES parties (organization_id, id),
  CONSTRAINT exclusive_relationship_no_overlap EXCLUDE USING gist (
    organization_id WITH =,
    subject_party_id WITH =,
    relationship_kind WITH =,
    tstzrange(effective_at, COALESCE(ended_at, 'infinity'), '[)') WITH &&
  ) WHERE (exclusive)
);

CREATE TABLE property_addresses (
  organization_id uuid NOT NULL,
  property_id uuid NOT NULL,
  line1 text NOT NULL,
  city text NOT NULL,
  region text NOT NULL,
  postal_code text NOT NULL,
  country text NOT NULL DEFAULT 'US',
  source_text text NOT NULL,
  PRIMARY KEY (organization_id, property_id),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id)
);

CREATE TABLE parcels (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  property_id uuid NOT NULL,
  jurisdiction text NOT NULL,
  parcel_identifier text NOT NULL,
  provenance text NOT NULL,
  UNIQUE (organization_id, jurisdiction, parcel_identifier),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id)
);

CREATE TABLE property_facts (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  property_id uuid NOT NULL,
  fact_key text NOT NULL,
  fact_value text NOT NULL,
  provenance text NOT NULL CHECK (provenance IN ('verified', 'imported', 'inferred')),
  confidence numeric(5, 4),
  verified_by uuid,
  verified_on date,
  expires_on date,
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  CHECK (provenance <> 'inferred' OR confidence IS NOT NULL),
  CHECK (provenance <> 'verified' OR (verified_by IS NOT NULL AND verified_on IS NOT NULL)),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id)
);

CREATE TABLE property_issues (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  property_id uuid NOT NULL,
  summary text NOT NULL CHECK (char_length(summary) BETWEEN 1 AND 500),
  severity text NOT NULL CHECK (severity IN ('information', 'review', 'material')),
  observed_on date NOT NULL,
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id)
);

CREATE TABLE documents (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  document_class text NOT NULL,
  title text NOT NULL CHECK (char_length(title) BETWEEN 1 AND 200),
  classification text NOT NULL CHECK (classification IN ('public', 'internal', 'confidential', 'restricted')),
  primary_resource_type text NOT NULL,
  primary_resource_id uuid NOT NULL,
  lifecycle text NOT NULL CHECK (lifecycle IN ('staged', 'scanning', 'available', 'quarantined', 'held')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (id)
);

CREATE TABLE document_versions (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL,
  version_number integer NOT NULL CHECK (version_number >= 1),
  object_key text NOT NULL,
  checksum_sha256 text NOT NULL,
  byte_size bigint NOT NULL CHECK (byte_size >= 0 AND byte_size <= 52428800),
  media_type text NOT NULL,
  original_filename text NOT NULL,
  scan_verdict text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, document_id, version_number),
  UNIQUE (organization_id, checksum_sha256, document_id),
  FOREIGN KEY (organization_id, document_id) REFERENCES documents (organization_id, id)
);

CREATE TABLE legal_holds (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  document_id uuid NOT NULL,
  reason text NOT NULL CHECK (char_length(reason) BETWEEN 3 AND 500),
  placed_by uuid NOT NULL,
  placed_at timestamptz NOT NULL DEFAULT now(),
  released_at timestamptz,
  release_reason text,
  CHECK (released_at IS NULL OR release_reason IS NOT NULL),
  FOREIGN KEY (organization_id, document_id) REFERENCES documents (organization_id, id)
);

CREATE TABLE retention_policies (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  document_class text NOT NULL,
  retain_days integer NOT NULL CHECK (retain_days > 0),
  policy_version integer NOT NULL CHECK (policy_version >= 1),
  provisional boolean NOT NULL DEFAULT true CHECK (provisional),
  UNIQUE (organization_id, document_class, policy_version)
);

CREATE TABLE search_documents (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  resource_type text NOT NULL,
  resource_id uuid NOT NULL,
  title text NOT NULL,
  body text NOT NULL DEFAULT '',
  classification text NOT NULL CHECK (classification IN ('public', 'internal', 'confidential', 'restricted')),
  search_vector tsvector GENERATED ALWAYS AS (
    setweight(to_tsvector('simple', coalesce(title, '')), 'A') ||
    setweight(to_tsvector('simple', coalesce(body, '')), 'B')
  ) STORED,
  updated_at timestamptz NOT NULL DEFAULT now(),
  UNIQUE (organization_id, resource_type, resource_id)
);

CREATE INDEX search_documents_vector ON search_documents USING gin (search_vector);
CREATE INDEX search_documents_title_trgm ON search_documents USING gin (title gin_trgm_ops);

CREATE TABLE saved_searches (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  actor_id uuid NOT NULL,
  query_text text NOT NULL CHECK (char_length(query_text) BETWEEN 2 AND 200),
  shared boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE import_batches (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (id),
  source_name text NOT NULL,
  content_sha256 text NOT NULL,
  status text NOT NULL CHECK (status IN ('staged', 'approved', 'applied', 'rejected')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE import_rows (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  batch_id uuid NOT NULL,
  source_row integer NOT NULL,
  raw_text text NOT NULL,
  normalized_name text,
  finding text NOT NULL CHECK (finding IN ('valid', 'blocker', 'warning', 'information')),
  finding_detail text NOT NULL,
  FOREIGN KEY (organization_id, batch_id) REFERENCES import_batches (organization_id, id)
);

CREATE TABLE quality_findings (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  resource_type text NOT NULL,
  resource_id uuid NOT NULL,
  severity text NOT NULL CHECK (severity IN ('blocker', 'review', 'information')),
  detail text NOT NULL,
  rule_version text NOT NULL,
  resolution text,
  resolved_by uuid,
  CHECK (resolution IS NULL OR resolved_by IS NOT NULL)
);

CREATE TABLE audit_digests (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  digest text NOT NULL,
  event_count integer NOT NULL CHECK (event_count >= 0),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TRIGGER audit_digest_no_update BEFORE UPDATE OR DELETE ON audit_digests
FOR EACH ROW EXECUTE FUNCTION perchpoint.reject_audit_mutation();

CREATE TRIGGER document_version_no_update BEFORE UPDATE OR DELETE ON document_versions
FOR EACH ROW EXECUTE FUNCTION perchpoint.reject_audit_mutation();

CREATE OR REPLACE FUNCTION perchpoint.public_search(query text)
RETURNS TABLE (resource_type text, resource_id uuid, title text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT resource_type, resource_id, title
  FROM search_documents
  WHERE classification = 'public'
    AND char_length(btrim(query)) >= 2
    AND (
      title ILIKE '%' || replace(replace(query, '%', ''), '_', '') || '%'
      OR search_vector @@ websearch_to_tsquery('simple', query)
    )
  LIMIT 20
$$;

REVOKE ALL ON FUNCTION perchpoint.public_search(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.public_search(text) TO perchpoint_runtime;
ALTER FUNCTION perchpoint.public_search(text) OWNER TO perchpoint_definer;

DO $$
DECLARE tbl text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'parties','party_relationships','property_addresses','parcels','property_facts','property_issues',
    'documents','document_versions','legal_holds','retention_policies','search_documents','saved_searches',
    'import_batches','import_rows','quality_findings','audit_digests'
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
  parties, party_relationships, property_addresses, parcels, property_facts, property_issues,
  documents, legal_holds, retention_policies, search_documents, saved_searches,
  import_batches, import_rows, quality_findings
TO perchpoint_runtime;
GRANT SELECT, INSERT ON document_versions, audit_digests TO perchpoint_runtime;

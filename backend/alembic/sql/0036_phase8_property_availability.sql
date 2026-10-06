-- Phase 8 extends the accepted property, building, space, and listing model.
-- It does not add syndication, CRM, applications, ledgers, or maintenance work orders.

ALTER TABLE properties
  ADD COLUMN IF NOT EXISTS lifecycle text NOT NULL DEFAULT 'active'
    CHECK (lifecycle IN ('onboarding', 'active', 'restricted', 'disposition_pending', 'inactive', 'archived')),
  ADD COLUMN IF NOT EXISTS reference_code text,
  ADD COLUMN IF NOT EXISTS time_zone text NOT NULL DEFAULT 'America/New_York';

CREATE UNIQUE INDEX IF NOT EXISTS properties_reference_code_key
  ON properties (organization_id, reference_code)
  WHERE reference_code IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS listings_organization_id_key
  ON listings (organization_id, id);

CREATE TABLE property_address_records (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  property_id uuid NOT NULL,
  building_id uuid,
  line1 text NOT NULL,
  locality text NOT NULL,
  region text NOT NULL,
  postal_code text NOT NULL,
  country text NOT NULL DEFAULT 'US',
  source text NOT NULL CHECK (source IN ('entered', 'normalized', 'manual_override')),
  current boolean NOT NULL DEFAULT true,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id),
  FOREIGN KEY (organization_id, building_id) REFERENCES buildings (organization_id, id)
);

CREATE UNIQUE INDEX property_address_records_current
  ON property_address_records (organization_id, property_id, COALESCE(building_id, '00000000-0000-0000-0000-000000000000'::uuid))
  WHERE current;

CREATE TABLE portfolio_memberships (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  property_id uuid NOT NULL,
  group_code text NOT NULL,
  effective_on date NOT NULL,
  ended_on date,
  PRIMARY KEY (organization_id, id),
  CHECK (ended_on IS NULL OR ended_on > effective_on),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id)
);

CREATE TABLE asking_prices (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor >= 0 AND amount_minor <= 100000000),
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  period text NOT NULL CHECK (period IN ('monthly', 'annual')),
  effective_on date NOT NULL,
  ended_on date,
  reason text NOT NULL,
  actor_id uuid NOT NULL,
  approval_state text NOT NULL CHECK (approval_state IN ('routine', 'owner_approved', 'exception_prepared')),
  PRIMARY KEY (organization_id, id),
  CHECK (ended_on IS NULL OR ended_on > effective_on),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE UNIQUE INDEX one_open_asking_price
  ON asking_prices (organization_id, space_id)
  WHERE ended_on IS NULL;

CREATE TABLE fee_components (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  code text NOT NULL,
  label text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  required boolean NOT NULL,
  recurring boolean NOT NULL,
  refundable boolean NOT NULL,
  effective_on date NOT NULL,
  ended_on date,
  PRIMARY KEY (organization_id, id),
  CHECK (ended_on IS NULL OR ended_on > effective_on),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE TABLE utility_responsibilities (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  utility_code text NOT NULL,
  responsibility text NOT NULL CHECK (responsibility IN ('included', 'tenant_paid', 'allocated', 'metered', 'unknown')),
  explanation text NOT NULL,
  effective_on date NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE TABLE concessions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  label text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  effective_on date NOT NULL,
  ended_on date NOT NULL,
  CHECK (ended_on > effective_on),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE TABLE pricing_exceptions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  proposed_amount_minor integer NOT NULL CHECK (proposed_amount_minor >= 0),
  reason text NOT NULL,
  status text NOT NULL CHECK (status IN ('prepared', 'reserved')),
  actor_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE TABLE space_readiness (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  readiness text NOT NULL CHECK (readiness IN (
    'not_assessed', 'occupied_not_turning', 'notice_pending', 'turn_required',
    'work_in_progress', 'inspection_required', 'ready', 'blocked'
  )),
  reason text NOT NULL,
  actor_id uuid NOT NULL,
  recorded_at timestamptz NOT NULL DEFAULT now(),
  current boolean NOT NULL DEFAULT true,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE UNIQUE INDEX one_current_readiness
  ON space_readiness (organization_id, space_id)
  WHERE current;

CREATE TABLE availability_statements (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  availability text NOT NULL CHECK (availability IN (
    'not_offered', 'coming_soon', 'available', 'temporary_hold',
    'application_pending', 'lease_pending', 'leased', 'off_market'
  )),
  effective_on date NOT NULL,
  confidence text NOT NULL CHECK (confidence IN ('exact', 'estimated')),
  source text NOT NULL,
  confirmed_at timestamptz NOT NULL,
  reason text NOT NULL,
  current boolean NOT NULL DEFAULT true,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE UNIQUE INDEX one_current_availability_statement
  ON availability_statements (organization_id, space_id)
  WHERE current;

CREATE TABLE availability_holds (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  reason text NOT NULL,
  holder_label text NOT NULL,
  expires_at timestamptz NOT NULL,
  released_at timestamptz,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE UNIQUE INDEX one_open_hold
  ON availability_holds (organization_id, space_id)
  WHERE released_at IS NULL;

CREATE TABLE listing_media_assets (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  space_id uuid NOT NULL,
  status text NOT NULL CHECK (status IN ('quarantine', 'rejected', 'approved', 'retired')),
  declared_mime text NOT NULL,
  content_sha256 text NOT NULL,
  alt_text text NOT NULL DEFAULT '',
  rights_state text NOT NULL CHECK (rights_state IN ('unknown', 'licensed', 'revoked')),
  review_state text NOT NULL CHECK (review_state IN ('pending', 'approved', 'rejected')),
  sort_order integer NOT NULL DEFAULT 0,
  primary_asset boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE UNIQUE INDEX one_primary_listing_asset
  ON listing_media_assets (organization_id, space_id)
  WHERE primary_asset AND status = 'approved';

CREATE TABLE listing_snapshots (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  listing_id uuid NOT NULL,
  space_id uuid NOT NULL,
  public_slug text NOT NULL,
  schema_version integer NOT NULL CHECK (schema_version = 1),
  content_hash text NOT NULL,
  payload jsonb NOT NULL,
  actor_id uuid NOT NULL,
  published_at timestamptz NOT NULL DEFAULT now(),
  superseded_at timestamptz,
  PRIMARY KEY (organization_id, id),
  CHECK (NOT (payload ? 'organization_id' OR payload ? 'resident' OR payload ? 'cost_minor' OR payload ? 'access_code' OR payload ? 'internal_note')),
  FOREIGN KEY (organization_id, listing_id) REFERENCES listings (organization_id, id),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE UNIQUE INDEX listing_snapshots_current
  ON listing_snapshots (organization_id, public_slug)
  WHERE superseded_at IS NULL;

CREATE TABLE phase8_jobs (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  job_kind text NOT NULL CHECK (job_kind IN ('hold_expiry', 'scheduled_unpublish', 'cache_repair')),
  aggregate_id uuid NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'leased', 'done', 'dead_letter')),
  attempts integer NOT NULL DEFAULT 0,
  available_at timestamptz NOT NULL,
  lease_until timestamptz,
  idempotency_key text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, idempotency_key)
);

ALTER TABLE property_address_records ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_address_records FORCE ROW LEVEL SECURITY;
ALTER TABLE portfolio_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE portfolio_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE asking_prices ENABLE ROW LEVEL SECURITY;
ALTER TABLE asking_prices FORCE ROW LEVEL SECURITY;
ALTER TABLE fee_components ENABLE ROW LEVEL SECURITY;
ALTER TABLE fee_components FORCE ROW LEVEL SECURITY;
ALTER TABLE utility_responsibilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE utility_responsibilities FORCE ROW LEVEL SECURITY;
ALTER TABLE concessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE concessions FORCE ROW LEVEL SECURITY;
ALTER TABLE pricing_exceptions ENABLE ROW LEVEL SECURITY;
ALTER TABLE pricing_exceptions FORCE ROW LEVEL SECURITY;
ALTER TABLE space_readiness ENABLE ROW LEVEL SECURITY;
ALTER TABLE space_readiness FORCE ROW LEVEL SECURITY;
ALTER TABLE availability_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE availability_statements FORCE ROW LEVEL SECURITY;
ALTER TABLE availability_holds ENABLE ROW LEVEL SECURITY;
ALTER TABLE availability_holds FORCE ROW LEVEL SECURITY;
ALTER TABLE listing_media_assets ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_media_assets FORCE ROW LEVEL SECURITY;
ALTER TABLE listing_snapshots ENABLE ROW LEVEL SECURITY;
ALTER TABLE listing_snapshots FORCE ROW LEVEL SECURITY;
ALTER TABLE phase8_jobs ENABLE ROW LEVEL SECURITY;
ALTER TABLE phase8_jobs FORCE ROW LEVEL SECURITY;

CREATE POLICY property_address_records_scope ON property_address_records
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY portfolio_memberships_scope ON portfolio_memberships
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY asking_prices_scope ON asking_prices
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY fee_components_scope ON fee_components
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY utility_responsibilities_scope ON utility_responsibilities
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY concessions_scope ON concessions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY pricing_exceptions_scope ON pricing_exceptions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY space_readiness_scope ON space_readiness
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY availability_statements_scope ON availability_statements
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY availability_holds_scope ON availability_holds
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY listing_media_assets_scope ON listing_media_assets
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY listing_snapshots_scope ON listing_snapshots
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY phase8_jobs_scope ON phase8_jobs
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));

GRANT SELECT, INSERT, UPDATE ON property_address_records, portfolio_memberships, asking_prices, fee_components,
  utility_responsibilities, concessions, pricing_exceptions, space_readiness, availability_statements,
  availability_holds, listing_media_assets, listing_snapshots, phase8_jobs TO perchpoint_runtime, perchpoint_definer;
REVOKE DELETE ON property_address_records, portfolio_memberships, asking_prices, fee_components,
  utility_responsibilities, concessions, pricing_exceptions, space_readiness, availability_statements,
  availability_holds, listing_media_assets, listing_snapshots, phase8_jobs FROM perchpoint_runtime;

CREATE FUNCTION perchpoint.published_listing_snapshot(slug text)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT payload FROM listing_snapshots
  WHERE public_slug = slug AND superseded_at IS NULL
  LIMIT 1
$$;

ALTER FUNCTION perchpoint.published_listing_snapshot(text) OWNER TO perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.published_listing_snapshot(text) TO perchpoint_runtime, perchpoint_definer;

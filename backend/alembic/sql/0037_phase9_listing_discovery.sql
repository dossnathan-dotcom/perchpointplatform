-- Phase 9 discovery projections are derived from immutable Phase 8 snapshots.
-- External syndication targets are rejected by the target constraint.

CREATE TABLE discovery_projections (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  listing_id uuid NOT NULL,
  snapshot_id uuid NOT NULL,
  public_slug text NOT NULL,
  schema_version integer NOT NULL CHECK (schema_version = 1),
  policy_version integer NOT NULL CHECK (policy_version >= 1),
  content_hash text NOT NULL,
  eligibility text NOT NULL CHECK (eligibility IN ('eligible', 'withdrawn', 'ineligible')),
  payload jsonb NOT NULL,
  search_text text NOT NULL,
  city text NOT NULL DEFAULT '',
  neighborhood text NOT NULL DEFAULT '',
  postal_code text NOT NULL DEFAULT '',
  use_code text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  currency text NOT NULL,
  period text NOT NULL,
  bedrooms integer,
  available_on date,
  sort_rank integer NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  current boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, snapshot_id) REFERENCES listing_snapshots (organization_id, id),
  CHECK (
    NOT (payload ? 'organization_id')
    AND NOT (payload ? 'resident')
    AND NOT (payload ? 'access_code')
    AND NOT (payload ? 'internal_note')
    AND NOT (payload ? 'cost_minor')
  )
);

CREATE UNIQUE INDEX discovery_current_listing
  ON discovery_projections (organization_id, listing_id) WHERE current;
CREATE UNIQUE INDEX discovery_current_slug
  ON discovery_projections (public_slug) WHERE current AND eligibility = 'eligible';
CREATE INDEX discovery_search_key
  ON discovery_projections (eligibility, use_code, amount_minor, sort_rank)
  WHERE current;

CREATE TABLE distribution_operations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  projection_id uuid NOT NULL,
  target_code text NOT NULL CHECK (target_code IN ('discovery_index', 'public_page', 'sitemap', 'link_preview', 'health')),
  operation text NOT NULL CHECK (operation IN ('publish', 'withdraw', 'repair')),
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  projection_version integer NOT NULL,
  priority integer NOT NULL,
  state text NOT NULL CHECK (state IN ('pending', 'leased', 'done', 'dead_letter', 'stale')),
  attempts integer NOT NULL DEFAULT 0,
  observed_hash text NOT NULL DEFAULT '',
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, idempotency_key),
  FOREIGN KEY (organization_id, projection_id) REFERENCES discovery_projections (organization_id, id)
);

CREATE TABLE reconciliation_runs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  expected_count integer NOT NULL,
  observed_count integer NOT NULL,
  repaired_count integer NOT NULL,
  status text NOT NULL,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE discovery_events (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  event_name text NOT NULL,
  listing_slug text NOT NULL DEFAULT '',
  session_ref text NOT NULL,
  classification text NOT NULL,
  source text NOT NULL DEFAULT '',
  medium text NOT NULL DEFAULT '',
  campaign text NOT NULL DEFAULT '',
  context jsonb NOT NULL,
  idempotency_key text NOT NULL,
  counted boolean NOT NULL DEFAULT false,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, idempotency_key),
  CHECK (
    NOT (context ? 'email')
    AND NOT (context ? 'phone')
    AND NOT (context ? 'name')
    AND NOT (context ? 'access_code')
  )
);

CREATE TABLE ranking_policies (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  version integer NOT NULL,
  reason text NOT NULL,
  actor_id uuid NOT NULL,
  effective_on date NOT NULL,
  PRIMARY KEY (organization_id, id)
);

ALTER TABLE discovery_projections ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_projections FORCE ROW LEVEL SECURITY;
ALTER TABLE distribution_operations ENABLE ROW LEVEL SECURITY;
ALTER TABLE distribution_operations FORCE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE reconciliation_runs FORCE ROW LEVEL SECURITY;
ALTER TABLE discovery_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE discovery_events FORCE ROW LEVEL SECURITY;
ALTER TABLE ranking_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE ranking_policies FORCE ROW LEVEL SECURITY;

CREATE POLICY discovery_projections_scope ON discovery_projections
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY distribution_operations_scope ON distribution_operations
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY reconciliation_runs_scope ON reconciliation_runs
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY discovery_events_scope ON discovery_events
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.manage'));
CREATE POLICY ranking_policies_scope ON ranking_policies
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('property.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('approval.owner'));

GRANT SELECT, INSERT, UPDATE ON discovery_projections, distribution_operations, reconciliation_runs, discovery_events, ranking_policies
  TO perchpoint_runtime, perchpoint_definer;
REVOKE DELETE ON discovery_projections, distribution_operations, reconciliation_runs, discovery_events, ranking_policies
  FROM perchpoint_runtime;

CREATE FUNCTION perchpoint.search_discovery(criteria jsonb)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  WITH matched AS (
    SELECT projection.public_slug, projection.payload, projection.sort_rank, projection.amount_minor,
           projection.use_code, projection.city, projection.version, projection.content_hash
    FROM discovery_projections projection
    WHERE projection.current
      AND projection.eligibility = 'eligible'
      AND (COALESCE(criteria->>'use_code', '') = '' OR projection.use_code = criteria->>'use_code')
      AND (COALESCE(criteria->>'city', '') = '' OR lower(projection.city) = lower(criteria->>'city'))
      AND (COALESCE(criteria->>'postal_code', '') = '' OR projection.postal_code = criteria->>'postal_code')
      AND (COALESCE(criteria->>'max_amount', '') = '' OR projection.amount_minor <= (criteria->>'max_amount')::integer)
      AND (COALESCE(criteria->>'min_bedrooms', '') = '' OR projection.bedrooms >= (criteria->>'min_bedrooms')::integer)
      AND (
        COALESCE(criteria->>'query', '') = ''
        OR to_tsvector('simple', projection.search_text) @@ plainto_tsquery('simple', criteria->>'query')
      )
  )
  SELECT jsonb_build_object(
    'total', (SELECT count(*) FROM matched),
    'records', COALESCE((
      SELECT jsonb_agg(jsonb_build_object(
        'public_slug', row.public_slug,
        'payload', row.payload,
        'sort_rank', row.sort_rank,
        'amount_minor', row.amount_minor,
        'use_code', row.use_code,
        'version', row.version,
        'content_hash', row.content_hash
      ) ORDER BY
        CASE WHEN criteria->>'sort' = 'price_asc' THEN row.amount_minor END ASC,
        row.sort_rank ASC,
        row.public_slug ASC)
      FROM (
        SELECT * FROM matched
        ORDER BY
          CASE WHEN criteria->>'sort' = 'price_asc' THEN amount_minor END ASC,
          sort_rank ASC,
          public_slug ASC
        LIMIT LEAST(GREATEST(COALESCE(NULLIF(criteria->>'limit', '')::integer, 20), 1), 50)
        OFFSET GREATEST(COALESCE(NULLIF(criteria->>'offset', '')::integer, 0), 0)
      ) row
    ), '[]'::jsonb),
    'facets', jsonb_build_object(
      'residential', (SELECT count(*) FROM matched WHERE use_code = 'residential'),
      'commercial', (SELECT count(*) FROM matched WHERE use_code = 'commercial')
    )
  );
$$;

CREATE FUNCTION perchpoint.published_discovery_listing(slug text)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT payload FROM discovery_projections
  WHERE public_slug = slug AND current AND eligibility = 'eligible'
  LIMIT 1;
$$;

CREATE FUNCTION perchpoint.discovery_sitemap()
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT COALESCE(jsonb_agg(jsonb_build_object('loc', '/rentals/' || public_slug, 'version', version) ORDER BY public_slug), '[]'::jsonb)
  FROM discovery_projections
  WHERE current AND eligibility = 'eligible';
$$;

CREATE FUNCTION perchpoint.record_discovery_event(
  slug text, event_name text, session_ref text, source text, medium text, campaign text, idempotency_key text, gpc boolean
) RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  existing_id uuid;
  existing_counted boolean;
  event_id uuid := gen_random_uuid();
BEGIN
  SELECT organization_id INTO org FROM discovery_projections WHERE public_slug = slug AND current LIMIT 1;
  IF org IS NULL THEN
    RETURN jsonb_build_object('found', false);
  END IF;
  SELECT id, counted INTO existing_id, existing_counted
  FROM discovery_events WHERE organization_id = org AND discovery_events.idempotency_key = record_discovery_event.idempotency_key;
  IF existing_id IS NOT NULL THEN
    RETURN jsonb_build_object('id', existing_id, 'replayed', true, 'counted', existing_counted);
  END IF;
  INSERT INTO discovery_events (
    organization_id, id, event_name, listing_slug, session_ref, classification, source, medium, campaign, context, idempotency_key, counted
  ) VALUES (
    org, event_id, event_name, slug, session_ref, CASE WHEN gpc THEN 'suppressed' ELSE 'prospect' END,
    left(source, 40), left(medium, 40), left(campaign, 40),
    jsonb_build_object('schema', 1, 'event_name', event_name), record_discovery_event.idempotency_key, NOT gpc
  );
  RETURN jsonb_build_object('id', event_id, 'classification', CASE WHEN gpc THEN 'suppressed' ELSE 'prospect' END, 'counted', NOT gpc);
END $$;

REVOKE ALL ON FUNCTION perchpoint.search_discovery(jsonb) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.published_discovery_listing(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.discovery_sitemap() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.search_discovery(jsonb) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.published_discovery_listing(text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.discovery_sitemap() TO perchpoint_runtime, perchpoint_definer;
REVOKE ALL ON FUNCTION perchpoint.record_discovery_event(text, text, text, text, text, text, text, boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.record_discovery_event(text, text, text, text, text, text, text, boolean) TO perchpoint_runtime, perchpoint_definer;

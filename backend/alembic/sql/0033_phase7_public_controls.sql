-- Phase 7 public analytics intake and redirect lookup. Events stay categorical.

CREATE FUNCTION perchpoint.published_redirect(lookup text)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT jsonb_build_object(
    'destination', redirect.destination_path,
    'status_code', redirect.status_code,
    'synthetic', true
  )
  FROM content_redirects redirect
  WHERE redirect.source_path = lookup
    AND redirect.organization_id = (
      SELECT publication.organization_id
      FROM content_publications publication
      WHERE publication.slug = 'contact' AND publication.superseded_at IS NULL
      LIMIT 1
    )
  LIMIT 1
$$;

ALTER FUNCTION perchpoint.published_redirect(text) OWNER TO perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.published_redirect(text) TO perchpoint_runtime, perchpoint_definer;


CREATE FUNCTION perchpoint.record_public_analytics(
  event_name text,
  event_consent text,
  event_properties jsonb
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  target_org uuid;
  new_id uuid := gen_random_uuid();
BEGIN
  IF event_name NOT IN (
    'page_view', 'listing_view', 'cta', 'inquiry_start', 'inquiry_validation',
    'inquiry_submit', 'apply_route', 'support_intent', 'maintenance_intent',
    'contact_category', 'sign_in_transition', 'delivery_failure'
  ) THEN
    RAISE EXCEPTION 'rejected' USING ERRCODE = '22023';
  END IF;
  IF event_consent NOT IN ('essential', 'optional') THEN
    RAISE EXCEPTION 'rejected' USING ERRCODE = '22023';
  END IF;
  IF event_properties ?| ARRAY['email', 'phone', 'name', 'message', 'body', 'password', 'access_code'] THEN
    RAISE EXCEPTION 'pii_rejected' USING ERRCODE = '22023';
  END IF;
  SELECT organization_id INTO target_org
  FROM content_publications
  WHERE slug = 'contact' AND superseded_at IS NULL
  LIMIT 1;
  IF target_org IS NULL THEN
    RAISE EXCEPTION 'intake_unavailable' USING ERRCODE = 'P0002';
  END IF;
  INSERT INTO analytics_events (organization_id, id, name, consent, properties)
  VALUES (target_org, new_id, event_name, event_consent, event_properties);
  RETURN jsonb_build_object('id', new_id, 'stored', true, 'synthetic', true);
END;
$$;

ALTER FUNCTION perchpoint.record_public_analytics(text, text, jsonb) OWNER TO perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.record_public_analytics(text, text, jsonb) TO perchpoint_runtime, perchpoint_definer;

-- Phase 7 public content, publication snapshots, redirects, and attributable intake.
-- Canonical listing facts stay on listings. The CMS cannot update them.

ALTER TABLE listings ADD COLUMN IF NOT EXISTS public_slug text;
CREATE UNIQUE INDEX IF NOT EXISTS listings_public_slug_key ON listings (public_slug) WHERE public_slug IS NOT NULL;

CREATE TABLE content_items (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  kind text NOT NULL CHECK (kind IN ('page', 'faq', 'resource', 'announcement', 'legal', 'navigation', 'channel')),
  audience text NOT NULL DEFAULT 'public',
  locale text NOT NULL DEFAULT 'en',
  slug text NOT NULL CHECK (slug ~ '^[a-z0-9]+(?:-[a-z0-9]+)*$'),
  risk_class text NOT NULL CHECK (risk_class IN ('routine', 'elevated')),
  owner_account_id uuid NOT NULL,
  review_on date,
  status text NOT NULL CHECK (status IN ('draft', 'in_review', 'approved', 'scheduled', 'published', 'expired', 'unpublished', 'archived', 'rejected')),
  version integer NOT NULL DEFAULT 1 CHECK (version > 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, locale, slug)
);

CREATE TABLE content_revisions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  item_id uuid NOT NULL,
  version integer NOT NULL CHECK (version > 0),
  blocks jsonb NOT NULL,
  author_id uuid NOT NULL,
  reason text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, item_id, version),
  FOREIGN KEY (organization_id, item_id) REFERENCES content_items (organization_id, id)
);

CREATE TABLE content_publications (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  item_id uuid NOT NULL,
  revision_id uuid NOT NULL,
  slug text NOT NULL,
  snapshot jsonb NOT NULL,
  actor_id uuid NOT NULL,
  published_at timestamptz NOT NULL DEFAULT now(),
  effective_until timestamptz,
  superseded_at timestamptz,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, item_id) REFERENCES content_items (organization_id, id),
  FOREIGN KEY (organization_id, revision_id) REFERENCES content_revisions (organization_id, id)
);

CREATE UNIQUE INDEX content_publications_current
  ON content_publications (organization_id, slug)
  WHERE superseded_at IS NULL;

CREATE TABLE content_redirects (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  source_path text NOT NULL CHECK (left(source_path, 1) = '/'),
  destination_path text NOT NULL CHECK (left(destination_path, 1) = '/' AND destination_path <> source_path),
  status_code integer NOT NULL CHECK (status_code IN (301, 302, 308)),
  actor_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, source_path)
);

CREATE TABLE public_submissions (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  intent text NOT NULL CHECK (intent IN (
    'rental_inquiry', 'application_help', 'resident_help', 'maintenance_routing',
    'vendor_business', 'accessibility', 'general'
  )),
  payload jsonb NOT NULL,
  consent_version text NOT NULL,
  source_page text NOT NULL,
  listing_slug text,
  first_touch text,
  last_touch text,
  correlation_id uuid NOT NULL,
  reference_code text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE submission_idempotency (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  payload_hash text NOT NULL,
  submission_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE TABLE analytics_events (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  name text NOT NULL,
  consent text NOT NULL CHECK (consent IN ('essential', 'optional')),
  properties jsonb NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

ALTER TABLE content_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_items FORCE ROW LEVEL SECURITY;
ALTER TABLE content_revisions ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_revisions FORCE ROW LEVEL SECURITY;
ALTER TABLE content_publications ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_publications FORCE ROW LEVEL SECURITY;
ALTER TABLE content_redirects ENABLE ROW LEVEL SECURITY;
ALTER TABLE content_redirects FORCE ROW LEVEL SECURITY;
ALTER TABLE public_submissions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public_submissions FORCE ROW LEVEL SECURITY;
ALTER TABLE submission_idempotency ENABLE ROW LEVEL SECURITY;
ALTER TABLE submission_idempotency FORCE ROW LEVEL SECURITY;
ALTER TABLE analytics_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE analytics_events FORCE ROW LEVEL SECURITY;

CREATE POLICY content_items_staff ON content_items
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.edit'));

CREATE POLICY content_revisions_staff ON content_revisions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.edit'));

CREATE POLICY content_publications_staff ON content_publications
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.publish'));

CREATE POLICY content_redirects_staff ON content_redirects
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.redirect'));

CREATE POLICY public_submissions_staff ON public_submissions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.report'))
  WITH CHECK (false);

CREATE POLICY submission_idempotency_staff ON submission_idempotency
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.report'))
  WITH CHECK (false);

CREATE POLICY analytics_events_staff ON analytics_events
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.report'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('content.report'));

GRANT SELECT, INSERT, UPDATE ON content_items TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON content_revisions TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT, UPDATE ON content_publications TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON content_redirects TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT ON public_submissions, submission_idempotency TO perchpoint_runtime;
GRANT SELECT, INSERT ON public_submissions, submission_idempotency TO perchpoint_definer;
GRANT INSERT ON outbox TO perchpoint_definer;
GRANT SELECT, INSERT ON analytics_events TO perchpoint_runtime, perchpoint_definer;
REVOKE UPDATE, DELETE ON content_revisions FROM perchpoint_runtime;
REVOKE DELETE ON content_items, content_publications, content_redirects, public_submissions FROM perchpoint_runtime;

CREATE FUNCTION perchpoint.guard_content_publication()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  risk text;
  author uuid;
  super boolean;
BEGIN
  SELECT rolsuper INTO super FROM pg_roles WHERE rolname = session_user;
  IF super THEN
    RETURN NEW;
  END IF;
  SELECT item.risk_class, revision.author_id INTO risk, author
  FROM content_items item
  JOIN content_revisions revision
    ON revision.organization_id = item.organization_id AND revision.id = NEW.revision_id
  WHERE item.organization_id = NEW.organization_id AND item.id = NEW.item_id;
  IF risk = 'elevated' THEN
    IF NOT perchpoint.has_capability('content.approve') THEN
      RAISE EXCEPTION 'elevated_approval_required' USING ERRCODE = '42501';
    END IF;
    IF author = perchpoint.current_actor() THEN
      RAISE EXCEPTION 'self_approval_denied' USING ERRCODE = '42501';
    END IF;
  ELSIF NOT perchpoint.has_capability('content.publish') THEN
    RAISE EXCEPTION 'publish_authority_required' USING ERRCODE = '42501';
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER content_publications_guard
  BEFORE INSERT ON content_publications
  FOR EACH ROW EXECUTE FUNCTION perchpoint.guard_content_publication();

DROP FUNCTION IF EXISTS perchpoint.published_listings();
CREATE FUNCTION perchpoint.published_listings()
RETURNS TABLE (
  listing_id uuid,
  space_id uuid,
  property_name text,
  label text,
  use text,
  municipality text,
  state text,
  publication text,
  availability text,
  amount_minor integer,
  currency text,
  public_slug text
)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT id, space_id, property_name, label, use, municipality, state, publication, availability, amount_minor, currency, public_slug
  FROM listings
  WHERE publication = 'published' AND availability = 'offerable' AND currency = 'USD'
$$;

CREATE FUNCTION perchpoint.published_page(lookup text)
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT jsonb_build_object(
    'slug', publication.slug,
    'snapshot', publication.snapshot,
    'published_at', publication.published_at,
    'synthetic', true
  )
  FROM content_publications publication
  WHERE publication.slug = lookup
    AND publication.superseded_at IS NULL
    AND (publication.effective_until IS NULL OR publication.effective_until > now())
  ORDER BY publication.published_at DESC
  LIMIT 1
$$;

CREATE FUNCTION perchpoint.published_navigation()
RETURNS jsonb
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT COALESCE(jsonb_agg(jsonb_build_object('slug', publication.slug, 'title', publication.snapshot->>'title') ORDER BY publication.slug), '[]'::jsonb)
  FROM content_publications publication
  JOIN content_items item ON item.organization_id = publication.organization_id AND item.id = publication.item_id
  WHERE publication.superseded_at IS NULL
    AND item.kind = 'page'
    AND item.status = 'published'
$$;

CREATE FUNCTION perchpoint.accept_public_submission(
  submission_intent text,
  submission_payload jsonb,
  submission_consent text,
  submission_source text,
  submission_listing text,
  submission_first text,
  submission_last text,
  submission_key text,
  submission_hash text,
  submission_correlation uuid
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  target_org uuid;
  existing_hash text;
  existing_id uuid;
  existing_reference text;
  new_id uuid := gen_random_uuid();
  reference text;
BEGIN
  IF submission_payload ? 'company_website' AND length(COALESCE(submission_payload->>'company_website', '')) > 0 THEN
    RAISE EXCEPTION 'rejected' USING ERRCODE = '22023';
  END IF;
  IF submission_payload ? 'attachment' THEN
    RAISE EXCEPTION 'attachments_rejected' USING ERRCODE = '22023';
  END IF;
  SELECT organization_id INTO target_org
  FROM content_publications
  WHERE slug = 'contact' AND superseded_at IS NULL
  LIMIT 1;
  IF target_org IS NULL THEN
    RAISE EXCEPTION 'intake_unavailable' USING ERRCODE = 'P0002';
  END IF;
  IF submission_intent = 'rental_inquiry' AND NOT EXISTS (
    SELECT 1 FROM listings
    WHERE public_slug = submission_listing
      AND organization_id = target_org
      AND publication = 'published'
      AND availability = 'offerable'
  ) THEN
    RAISE EXCEPTION 'listing_unavailable' USING ERRCODE = 'P0002';
  END IF;
  SELECT payload_hash, submission_id INTO existing_hash, existing_id
  FROM submission_idempotency
  WHERE organization_id = target_org AND idempotency_key = submission_key;
  IF existing_id IS NOT NULL THEN
    IF existing_hash <> submission_hash THEN
      RAISE EXCEPTION 'idempotency_conflict' USING ERRCODE = '23505';
    END IF;
    SELECT reference_code INTO existing_reference FROM public_submissions WHERE id = existing_id;
    RETURN jsonb_build_object('id', existing_id, 'reference', existing_reference, 'replayed', true, 'synthetic', true);
  END IF;
  reference := 'HV-' || upper(substr(replace(new_id::text, '-', ''), 1, 8));
  INSERT INTO public_submissions (
    organization_id, id, intent, payload, consent_version, source_page, listing_slug,
    first_touch, last_touch, correlation_id, reference_code
  ) VALUES (
    target_org, new_id, submission_intent, submission_payload, submission_consent, submission_source,
    submission_listing, submission_first, submission_last, submission_correlation, reference
  );
  INSERT INTO submission_idempotency (organization_id, idempotency_key, payload_hash, submission_id)
  VALUES (target_org, submission_key, submission_hash, new_id);
  INSERT INTO outbox (organization_id, id, event_type, aggregate_id, payload, status, available_at)
  VALUES (
    target_org, gen_random_uuid(), 'public.submission.accepted', new_id,
    jsonb_build_object('intent', submission_intent, 'reference', reference, 'synthetic', true),
    'pending', now()
  );
  RETURN jsonb_build_object('id', new_id, 'reference', reference, 'replayed', false, 'synthetic', true);
END;
$$;

ALTER FUNCTION perchpoint.published_listings() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.published_page(text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.published_navigation() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.accept_public_submission(text, jsonb, text, text, text, text, text, text, text, uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.guard_content_publication() OWNER TO perchpoint_definer;

GRANT EXECUTE ON FUNCTION perchpoint.published_listings() TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.published_page(text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.published_navigation() TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.accept_public_submission(text, jsonb, text, text, text, text, text, text, text, uuid) TO perchpoint_runtime, perchpoint_definer;

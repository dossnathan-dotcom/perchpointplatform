-- Phase 10 leasing inquiries are canonical CRM records.
-- Phase 2 inquiries stay on their existing path. No showing, application, or marketplace table is created.

CREATE TABLE prospects (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  display_name text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('person', 'business')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  merged_into uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, merged_into) REFERENCES prospects (organization_id, id)
);

CREATE TABLE prospect_contacts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  prospect_id uuid NOT NULL,
  kind text NOT NULL CHECK (kind IN ('email', 'phone')),
  entered text NOT NULL,
  normalized text NOT NULL,
  verification text NOT NULL CHECK (verification IN ('unverified', 'verified')),
  suppressed boolean NOT NULL DEFAULT false,
  provenance text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, prospect_id) REFERENCES prospects (organization_id, id)
);

CREATE UNIQUE INDEX prospect_contact_identity
  ON prospect_contacts (organization_id, kind, normalized)
  WHERE suppressed = false;

CREATE TABLE prospect_consents (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  prospect_id uuid NOT NULL,
  purpose text NOT NULL CHECK (purpose IN ('inquiry', 'transactional', 'marketing')),
  channel text NOT NULL CHECK (channel IN ('email', 'phone', 'none')),
  status text NOT NULL CHECK (status IN ('granted', 'revoked')),
  policy_version integer NOT NULL,
  evidence text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, prospect_id) REFERENCES prospects (organization_id, id)
);

CREATE TABLE leasing_inquiries (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  prospect_id uuid NOT NULL,
  origin_prospect_id uuid NOT NULL,
  public_receipt text NOT NULL,
  source text NOT NULL CHECK (source IN ('website', 'phone', 'walk_in', 'forwarded')),
  stage text NOT NULL CHECK (stage IN ('new', 'assigned', 'contact_attempted', 'engaged', 'next_step_ready', 'nurture', 'closed', 'duplicate', 'spam')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  general_interest boolean NOT NULL DEFAULT false,
  received_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (public_receipt),
  FOREIGN KEY (organization_id, prospect_id) REFERENCES prospects (organization_id, id),
  FOREIGN KEY (organization_id, origin_prospect_id) REFERENCES prospects (organization_id, id)
);

CREATE TABLE leasing_interests (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  public_slug text NOT NULL,
  snapshot_id uuid,
  availability_state text NOT NULL,
  search_ref text NOT NULL DEFAULT '',
  result_position integer,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE TABLE leasing_attributions (
  organization_id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  direct_source text NOT NULL,
  first_touch text NOT NULL DEFAULT '',
  last_touch text NOT NULL DEFAULT '',
  gpc boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, inquiry_id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE TABLE inquiry_stage_episodes (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  stage text NOT NULL,
  reason text NOT NULL DEFAULT '',
  started_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  current boolean NOT NULL DEFAULT true,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE UNIQUE INDEX inquiry_one_current_stage
  ON inquiry_stage_episodes (organization_id, inquiry_id) WHERE current;

CREATE TABLE inquiry_assignments (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  account_id uuid,
  reason text NOT NULL,
  current boolean NOT NULL DEFAULT true,
  effective_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE UNIQUE INDEX inquiry_one_current_assignment
  ON inquiry_assignments (organization_id, inquiry_id) WHERE current;

CREATE TABLE inquiry_clocks (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  policy_version integer NOT NULL,
  zone_name text NOT NULL,
  started_at timestamptz NOT NULL,
  deadline_at timestamptz NOT NULL,
  qualified_at timestamptz,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE TABLE inquiry_actions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  kind text NOT NULL,
  status text NOT NULL CHECK (status IN ('open', 'done', 'cancelled')),
  is_primary boolean NOT NULL DEFAULT false,
  due_at timestamptz NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE UNIQUE INDEX inquiry_one_primary_action
  ON inquiry_actions (organization_id, inquiry_id) WHERE is_primary AND status = 'open';

CREATE TABLE leasing_notes (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  body text NOT NULL CHECK (length(body) <= 500 AND position('<' in body) = 0),
  author_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE TABLE leasing_tag_definitions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  code text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, code),
  CHECK (code NOT IN ('race', 'religion', 'family_status', 'national_origin', 'disability', 'desirability', 'screening', 'income_score'))
);

CREATE TABLE contact_attempts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  channel text NOT NULL,
  direction text NOT NULL,
  outcome text NOT NULL,
  suppressed boolean NOT NULL,
  summary text NOT NULL,
  actor_id uuid NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE TABLE duplicate_candidates (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  left_prospect uuid NOT NULL,
  right_prospect uuid NOT NULL,
  reason_code text NOT NULL,
  status text NOT NULL CHECK (status IN ('open', 'dismissed', 'merged')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, left_prospect) REFERENCES prospects (organization_id, id),
  FOREIGN KEY (organization_id, right_prospect) REFERENCES prospects (organization_id, id)
);

CREATE TABLE prospect_merges (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  survivor_id uuid NOT NULL,
  alias_id uuid NOT NULL,
  reason text NOT NULL,
  actor_id uuid NOT NULL,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE delivery_attempts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  channel text NOT NULL,
  state text NOT NULL CHECK (state IN ('queued', 'sent', 'failed', 'suppressed')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

CREATE TABLE leasing_intake_keys (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  receipt text NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE TABLE saved_views (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  owner_id uuid NOT NULL,
  name text NOT NULL,
  filter_json jsonb NOT NULL,
  shared boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE business_closures (
  organization_id uuid NOT NULL,
  closed_on date NOT NULL,
  reason text NOT NULL,
  PRIMARY KEY (organization_id, closed_on)
);

CREATE TABLE leasing_activities (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  action text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id)
);

ALTER TABLE prospects ENABLE ROW LEVEL SECURITY;
ALTER TABLE prospects FORCE ROW LEVEL SECURITY;
ALTER TABLE prospect_contacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE prospect_contacts FORCE ROW LEVEL SECURITY;
ALTER TABLE prospect_consents ENABLE ROW LEVEL SECURITY;
ALTER TABLE prospect_consents FORCE ROW LEVEL SECURITY;
ALTER TABLE leasing_inquiries ENABLE ROW LEVEL SECURITY;
ALTER TABLE leasing_inquiries FORCE ROW LEVEL SECURITY;
ALTER TABLE leasing_interests ENABLE ROW LEVEL SECURITY;
ALTER TABLE leasing_interests FORCE ROW LEVEL SECURITY;
ALTER TABLE leasing_attributions ENABLE ROW LEVEL SECURITY;
ALTER TABLE leasing_attributions FORCE ROW LEVEL SECURITY;
ALTER TABLE inquiry_stage_episodes ENABLE ROW LEVEL SECURITY;
ALTER TABLE inquiry_stage_episodes FORCE ROW LEVEL SECURITY;
ALTER TABLE inquiry_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE inquiry_assignments FORCE ROW LEVEL SECURITY;
ALTER TABLE inquiry_clocks ENABLE ROW LEVEL SECURITY;
ALTER TABLE inquiry_clocks FORCE ROW LEVEL SECURITY;
ALTER TABLE inquiry_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE inquiry_actions FORCE ROW LEVEL SECURITY;
ALTER TABLE leasing_notes ENABLE ROW LEVEL SECURITY;
ALTER TABLE leasing_notes FORCE ROW LEVEL SECURITY;
ALTER TABLE leasing_tag_definitions ENABLE ROW LEVEL SECURITY;
ALTER TABLE leasing_tag_definitions FORCE ROW LEVEL SECURITY;
ALTER TABLE contact_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE contact_attempts FORCE ROW LEVEL SECURITY;
ALTER TABLE duplicate_candidates ENABLE ROW LEVEL SECURITY;
ALTER TABLE duplicate_candidates FORCE ROW LEVEL SECURITY;
ALTER TABLE prospect_merges ENABLE ROW LEVEL SECURITY;
ALTER TABLE prospect_merges FORCE ROW LEVEL SECURITY;
ALTER TABLE delivery_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE delivery_attempts FORCE ROW LEVEL SECURITY;
ALTER TABLE leasing_intake_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE leasing_intake_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE saved_views ENABLE ROW LEVEL SECURITY;
ALTER TABLE saved_views FORCE ROW LEVEL SECURITY;
ALTER TABLE business_closures ENABLE ROW LEVEL SECURITY;
ALTER TABLE business_closures FORCE ROW LEVEL SECURITY;
ALTER TABLE leasing_activities ENABLE ROW LEVEL SECURITY;
ALTER TABLE leasing_activities FORCE ROW LEVEL SECURITY;

CREATE POLICY prospects_scope ON prospects
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY prospect_contacts_scope ON prospect_contacts
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY prospect_consents_scope ON prospect_consents
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY leasing_inquiries_scope ON leasing_inquiries
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY leasing_interests_scope ON leasing_interests
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY leasing_attributions_scope ON leasing_attributions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY inquiry_stage_episodes_scope ON inquiry_stage_episodes
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY inquiry_assignments_scope ON inquiry_assignments
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY inquiry_clocks_scope ON inquiry_clocks
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY inquiry_actions_scope ON inquiry_actions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY leasing_notes_scope ON leasing_notes
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY leasing_tag_definitions_scope ON leasing_tag_definitions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY contact_attempts_scope ON contact_attempts
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY duplicate_candidates_scope ON duplicate_candidates
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY prospect_merges_scope ON prospect_merges
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY delivery_attempts_scope ON delivery_attempts
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY leasing_intake_keys_scope ON leasing_intake_keys
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY saved_views_scope ON saved_views
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY business_closures_scope ON business_closures
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY leasing_activities_scope ON leasing_activities
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));

GRANT SELECT, INSERT, UPDATE ON prospects, prospect_contacts, prospect_consents, leasing_inquiries, leasing_interests,
  leasing_attributions, inquiry_stage_episodes, inquiry_assignments, inquiry_clocks, inquiry_actions, leasing_notes,
  leasing_tag_definitions, contact_attempts, duplicate_candidates, prospect_merges, delivery_attempts, leasing_intake_keys,
  saved_views, leasing_activities, business_closures
  TO perchpoint_runtime, perchpoint_definer;

CREATE FUNCTION perchpoint.leasing_deadline(received timestamptz, org uuid)
RETURNS timestamptz
LANGUAGE plpgsql STABLE SET search_path = public, pg_temp AS $$
DECLARE
  local_ts timestamp;
  dow integer;
BEGIN
  local_ts := received AT TIME ZONE 'America/New_York';
  dow := EXTRACT(DOW FROM local_ts)::integer;
  IF dow BETWEEN 1 AND 5
     AND EXTRACT(HOUR FROM local_ts) >= 9
     AND EXTRACT(HOUR FROM local_ts) < 15
     AND NOT EXISTS (SELECT 1 FROM business_closures WHERE organization_id = org AND closed_on = local_ts::date) THEN
    RETURN received + interval '2 hours';
  END IF;
  IF dow BETWEEN 1 AND 5 AND EXTRACT(HOUR FROM local_ts) < 9
     AND NOT EXISTS (SELECT 1 FROM business_closures WHERE organization_id = org AND closed_on = local_ts::date) THEN
    RETURN (date_trunc('day', local_ts) + interval '11 hours') AT TIME ZONE 'America/New_York';
  END IF;
  LOOP
    local_ts := date_trunc('day', local_ts) + interval '1 day';
    dow := EXTRACT(DOW FROM local_ts)::integer;
    EXIT WHEN dow BETWEEN 1 AND 5
      AND NOT EXISTS (SELECT 1 FROM business_closures WHERE organization_id = org AND closed_on = local_ts::date);
  END LOOP;
  RETURN (date_trunc('day', local_ts) + interval '11 hours') AT TIME ZONE 'America/New_York';
END $$;

CREATE FUNCTION perchpoint.capture_leasing_inquiry(intake jsonb, idempotency_key text, fingerprint text, gpc boolean)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  slug text;
  snap uuid;
  eligible text;
  existing_fp text;
  existing_receipt text;
  prospect uuid;
  inquiry uuid := gen_random_uuid();
  receipt text := replace(gen_random_uuid()::text, '-', '');
  email text := lower(btrim(COALESCE(intake->>'email', '')));
  phone text := regexp_replace(COALESCE(intake->>'phone', ''), '[^0-9]', '', 'g');
  person_name text := btrim(COALESCE(intake->>'name', ''));
  message text := left(regexp_replace(COALESCE(intake->>'message', ''), '[<>]', '', 'g'), 500);
  general boolean := false;
  deadline timestamptz;
  other uuid;
  delivery_state text;
  slug_item text;
BEGIN
  IF intake ? 'organization_id' OR intake ? 'snapshot_id' OR intake ? 'prospect_id' OR intake ? 'lead_score' OR intake ? 'tenant_quality' OR intake ? 'attachment' THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  IF COALESCE(intake->>'honeypot', '') <> '' OR COALESCE(intake->>'disclosure', '') <> 'true' THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  IF length(person_name) < 2 OR (email = '' AND phone = '') OR (email <> '' AND position('@' IN email) = 0) OR length(COALESCE(intake->>'message', '')) > 1000 THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  IF COALESCE(intake->>'public_slug', '') <> '' THEN
    SELECT organization_id, snapshot_id, eligibility INTO org, snap, eligible
    FROM discovery_projections WHERE public_slug = intake->>'public_slug' AND current LIMIT 1;
    IF org IS NULL THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
    END IF;
    general := eligible <> 'eligible';
  ELSIF COALESCE(intake->>'slugs', '') <> '' THEN
    FOREACH slug_item IN ARRAY string_to_array(intake->>'slugs', ',') LOOP
      SELECT organization_id INTO org FROM discovery_projections WHERE public_slug = btrim(slug_item) AND current LIMIT 1;
      IF org IS NULL THEN
        RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
      END IF;
    END LOOP;
  ELSE
    general := true;
    SELECT id INTO org FROM organizations WHERE name LIKE 'HawkVision%' ORDER BY name LIMIT 1;
    IF org IS NULL THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
    END IF;
  END IF;
  SELECT leasing_intake_keys.fingerprint, leasing_intake_keys.receipt INTO existing_fp, existing_receipt
  FROM leasing_intake_keys WHERE organization_id = org AND leasing_intake_keys.idempotency_key = capture_leasing_inquiry.idempotency_key;
  IF existing_fp IS NOT NULL THEN
    IF existing_fp <> fingerprint THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
    END IF;
    RETURN jsonb_build_object('accepted', true, 'receipt', existing_receipt, 'replayed', true);
  END IF;
  IF email <> '' THEN
    SELECT prospect_id INTO prospect FROM prospect_contacts
    WHERE organization_id = org AND kind = 'email' AND normalized = email AND suppressed = false LIMIT 1;
  END IF;
  IF prospect IS NULL THEN
    prospect := gen_random_uuid();
    INSERT INTO prospects (organization_id, id, display_name, kind) VALUES (org, prospect, person_name, 'person');
  END IF;
  IF email <> '' AND NOT EXISTS (
    SELECT 1 FROM prospect_contacts WHERE organization_id = org AND prospect_id = prospect AND kind = 'email' AND normalized = email
  ) THEN
    INSERT INTO prospect_contacts (organization_id, id, prospect_id, kind, entered, normalized, verification, provenance)
    VALUES (org, gen_random_uuid(), prospect, 'email', intake->>'email', email, 'unverified', 'website');
  END IF;
  IF phone <> '' AND NOT EXISTS (
    SELECT 1 FROM prospect_contacts WHERE organization_id = org AND prospect_id = prospect AND kind = 'phone' AND normalized = phone
  ) THEN
    INSERT INTO prospect_contacts (organization_id, id, prospect_id, kind, entered, normalized, verification, provenance)
    VALUES (org, gen_random_uuid(), prospect, 'phone', intake->>'phone', phone, 'unverified', 'website');
  END IF;
  SELECT id INTO other FROM prospects
  WHERE organization_id = org AND id <> prospect AND lower(display_name) = lower(person_name) LIMIT 1;
  IF other IS NOT NULL THEN
    INSERT INTO duplicate_candidates (organization_id, id, left_prospect, right_prospect, reason_code, status)
    VALUES (org, gen_random_uuid(), prospect, other, 'same_name', 'open');
  END IF;
  deadline := perchpoint.leasing_deadline(now(), org);
  INSERT INTO leasing_inquiries (organization_id, id, prospect_id, origin_prospect_id, public_receipt, source, stage, general_interest)
  VALUES (org, inquiry, prospect, prospect, receipt, 'website', 'new', general);
  IF COALESCE(intake->>'public_slug', '') <> '' THEN
    INSERT INTO leasing_interests (organization_id, id, inquiry_id, public_slug, snapshot_id, availability_state, search_ref, result_position)
    VALUES (org, gen_random_uuid(), inquiry, intake->>'public_slug', snap, CASE WHEN general THEN 'historical' ELSE 'available' END, COALESCE(intake->>'search_ref', ''), NULLIF(intake->>'position', '')::integer);
  END IF;
  IF COALESCE(intake->>'slugs', '') <> '' THEN
    FOREACH slug_item IN ARRAY string_to_array(intake->>'slugs', ',') LOOP
      INSERT INTO leasing_interests (organization_id, id, inquiry_id, public_slug, snapshot_id, availability_state, search_ref)
      SELECT org, gen_random_uuid(), inquiry, projection.public_slug, projection.snapshot_id, 'available', COALESCE(intake->>'search_ref', '')
      FROM discovery_projections projection
      WHERE projection.public_slug = btrim(slug_item) AND projection.current;
    END LOOP;
  END IF;
  INSERT INTO leasing_attributions (organization_id, inquiry_id, direct_source, first_touch, last_touch, gpc)
  VALUES (org, inquiry, 'website', COALESCE(intake->>'first_touch', ''), COALESCE(intake->>'last_touch', ''), gpc);
  INSERT INTO prospect_consents (organization_id, id, prospect_id, purpose, channel, status, policy_version, evidence)
  VALUES (org, gen_random_uuid(), prospect, 'inquiry', CASE WHEN email <> '' THEN 'email' ELSE 'phone' END, 'granted', 1, 'disclosure');
  IF COALESCE(intake->>'marketing_opt_in', '') = 'true' AND NOT gpc THEN
    INSERT INTO prospect_consents (organization_id, id, prospect_id, purpose, channel, status, policy_version, evidence)
    VALUES (org, gen_random_uuid(), prospect, 'marketing', 'email', 'granted', 1, 'opt_in');
  END IF;
  INSERT INTO inquiry_stage_episodes (organization_id, id, inquiry_id, stage, reason) VALUES (org, gen_random_uuid(), inquiry, 'new', 'intake');
  INSERT INTO inquiry_assignments (organization_id, id, inquiry_id, account_id, reason) VALUES (org, gen_random_uuid(), inquiry, NULL, 'awaiting_claim');
  INSERT INTO inquiry_clocks (organization_id, id, inquiry_id, policy_version, zone_name, started_at, deadline_at)
  VALUES (org, gen_random_uuid(), inquiry, 1, 'America/New_York', now(), deadline);
  INSERT INTO inquiry_actions (organization_id, id, inquiry_id, kind, status, is_primary, due_at)
  VALUES (org, gen_random_uuid(), inquiry, 'review_inquiry', 'open', true, deadline);
  delivery_state := CASE WHEN COALESCE(intake->>'fail_delivery', '') = 'true' THEN 'failed' ELSE 'sent' END;
  INSERT INTO delivery_attempts (organization_id, id, inquiry_id, channel, state) VALUES (org, gen_random_uuid(), inquiry, 'email', delivery_state);
  INSERT INTO leasing_activities (organization_id, id, inquiry_id, action) VALUES (org, gen_random_uuid(), inquiry, 'inquiry.received');
  INSERT INTO leasing_intake_keys (organization_id, idempotency_key, fingerprint, receipt)
  VALUES (org, capture_leasing_inquiry.idempotency_key, fingerprint, receipt);
  RETURN jsonb_build_object('accepted', true, 'receipt', receipt, 'replayed', false);
END $$;

REVOKE ALL ON FUNCTION perchpoint.capture_leasing_inquiry(jsonb, text, text, boolean) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.capture_leasing_inquiry(jsonb, text, text, boolean) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.leasing_deadline(timestamptz, uuid) TO perchpoint_runtime, perchpoint_definer;
ALTER FUNCTION perchpoint.capture_leasing_inquiry(jsonb, text, text, boolean) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.leasing_deadline(timestamptz, uuid) OWNER TO perchpoint_definer;

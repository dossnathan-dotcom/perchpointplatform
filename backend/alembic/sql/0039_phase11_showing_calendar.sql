-- Phase 11 canonical showings. Provider calendars are mirrors. No application or lockbox table is created.

CREATE TABLE showing_policies (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  duration_minutes integer NOT NULL DEFAULT 30 CHECK (duration_minutes = 30),
  buffer_minutes integer NOT NULL DEFAULT 15 CHECK (buffer_minutes = 15),
  lead_hours integer NOT NULL DEFAULT 2 CHECK (lead_hours = 2),
  horizon_days integer NOT NULL DEFAULT 30 CHECK (horizon_days = 30),
  step_minutes integer NOT NULL DEFAULT 15 CHECK (step_minutes = 15),
  hold_minutes integer NOT NULL DEFAULT 5 CHECK (hold_minutes = 5),
  zone_name text NOT NULL DEFAULT 'America/New_York',
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE showing_resources (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  kind text NOT NULL CHECK (kind IN ('property', 'space', 'host', 'session')),
  parent_id uuid,
  label text NOT NULL,
  capacity integer NOT NULL DEFAULT 1 CHECK (capacity BETWEEN 1 AND 50),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, parent_id) REFERENCES showing_resources (organization_id, id),
  CHECK (parent_id IS DISTINCT FROM id)
);

CREATE FUNCTION perchpoint.showing_resource_no_cycle()
RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  cursor_id uuid := NEW.parent_id;
  depth integer := 0;
BEGIN
  WHILE cursor_id IS NOT NULL LOOP
    IF cursor_id = NEW.id OR depth > 8 THEN
      RAISE EXCEPTION 'resource_cycle' USING ERRCODE = '23514';
    END IF;
    SELECT parent_id INTO cursor_id FROM showing_resources
    WHERE organization_id = NEW.organization_id AND id = cursor_id;
    depth := depth + 1;
  END LOOP;
  RETURN NEW;
END $$;

CREATE TRIGGER showing_resources_no_cycle
BEFORE INSERT OR UPDATE OF parent_id ON showing_resources
FOR EACH ROW EXECUTE FUNCTION perchpoint.showing_resource_no_cycle();

CREATE TABLE showings (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  prospect_id uuid NOT NULL,
  public_reference text NOT NULL,
  mode text NOT NULL CHECK (mode IN ('individual', 'group', 'remote')),
  business_state text NOT NULL CHECK (business_state IN ('confirmed', 'completed', 'cancelled', 'no_show')),
  sync_state text NOT NULL DEFAULT 'pending' CHECK (sync_state IN ('pending', 'synced', 'drifted', 'failed', 'disconnected')),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  wall_start text NOT NULL,
  zone_name text NOT NULL,
  offset_minutes integer NOT NULL,
  starts_at timestamptz NOT NULL,
  ends_at timestamptz NOT NULL,
  host_resource_id uuid NOT NULL,
  space_resource_id uuid NOT NULL,
  guest_count integer NOT NULL DEFAULT 1 CHECK (guest_count BETWEEN 1 AND 20),
  policy_version integer NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (public_reference),
  FOREIGN KEY (organization_id, inquiry_id) REFERENCES leasing_inquiries (organization_id, id),
  FOREIGN KEY (organization_id, host_resource_id) REFERENCES showing_resources (organization_id, id),
  FOREIGN KEY (organization_id, space_resource_id) REFERENCES showing_resources (organization_id, id),
  CHECK (ends_at > starts_at)
);

CREATE TABLE showing_occupancy (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  resource_id uuid NOT NULL,
  showing_id uuid,
  hold_id uuid,
  span tstzrange NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, resource_id) REFERENCES showing_resources (organization_id, id),
  CHECK (lower(span) IS NOT NULL AND upper(span) IS NOT NULL AND span <> 'empty'),
  CONSTRAINT showing_occupancy_no_overlap EXCLUDE USING gist (
    organization_id WITH =,
    resource_id WITH =,
    span WITH &&
  )
);

CREATE TABLE showing_holds (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  inquiry_id uuid NOT NULL,
  resource_id uuid NOT NULL,
  capability_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  state text NOT NULL CHECK (state IN ('active', 'converted', 'expired', 'released')),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE showing_capabilities (
  organization_id uuid NOT NULL,
  token_hash text NOT NULL,
  inquiry_id uuid NOT NULL,
  purpose text NOT NULL CHECK (purpose IN ('book', 'change')),
  expires_at timestamptz NOT NULL,
  revoked boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, token_hash)
);

CREATE TABLE showing_intake_keys (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE TABLE showing_seat_uses (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  resource_id uuid NOT NULL,
  showing_id uuid NOT NULL,
  guests integer NOT NULL CHECK (guests > 0),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, resource_id) REFERENCES showing_resources (organization_id, id)
);

CREATE FUNCTION perchpoint.showing_seats_within_capacity()
RETURNS trigger
LANGUAGE plpgsql SET search_path = public, pg_temp AS $$
DECLARE
  allowed integer;
  taken integer;
BEGIN
  PERFORM 1 FROM showing_resources
  WHERE organization_id = NEW.organization_id AND id = NEW.resource_id
  FOR UPDATE;
  SELECT capacity INTO allowed FROM showing_resources
  WHERE organization_id = NEW.organization_id AND id = NEW.resource_id;
  SELECT COALESCE(SUM(guests), 0) INTO taken FROM showing_seat_uses
  WHERE organization_id = NEW.organization_id AND resource_id = NEW.resource_id;
  IF taken > allowed THEN
    RAISE EXCEPTION 'capacity_exceeded' USING ERRCODE = '23514';
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER showing_seat_uses_capacity
AFTER INSERT ON showing_seat_uses
FOR EACH ROW EXECUTE FUNCTION perchpoint.showing_seats_within_capacity();

CREATE TABLE calendar_connections (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  account_id uuid NOT NULL,
  provider_code text NOT NULL CHECK (provider_code = 'fake'),
  token_envelope text NOT NULL,
  token_version integer NOT NULL DEFAULT 1,
  state text NOT NULL CHECK (state IN ('pending', 'active', 'revoked', 'disconnected')),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE calendar_busy (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  connection_id uuid NOT NULL,
  span tstzrange NOT NULL,
  semantic text NOT NULL CHECK (semantic IN ('busy', 'ooo', 'tentative', 'transparent', 'all_day')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, connection_id) REFERENCES calendar_connections (organization_id, id)
);

CREATE TABLE showing_sync (
  organization_id uuid NOT NULL,
  showing_id uuid NOT NULL,
  desired_hash text NOT NULL,
  observed_hash text NOT NULL DEFAULT '',
  state text NOT NULL CHECK (state IN ('pending', 'synced', 'drifted', 'failed')),
  PRIMARY KEY (organization_id, showing_id),
  FOREIGN KEY (organization_id, showing_id) REFERENCES showings (organization_id, id)
);

CREATE TABLE showing_callbacks (
  organization_id uuid NOT NULL,
  provider_event_id text NOT NULL,
  change_kind text NOT NULL,
  PRIMARY KEY (organization_id, provider_event_id)
);

CREATE TABLE showing_deliveries (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  showing_id uuid NOT NULL,
  purpose text NOT NULL,
  state text NOT NULL CHECK (state IN ('queued', 'sent', 'failed', 'suppressed', 'cancelled')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, showing_id) REFERENCES showings (organization_id, id)
);

CREATE TABLE showing_impacts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  showing_id uuid NOT NULL,
  reason text NOT NULL,
  state text NOT NULL CHECK (state IN ('open', 'resolved')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, showing_id) REFERENCES showings (organization_id, id)
);

ALTER TABLE showing_policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_policies FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_resources ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_resources FORCE ROW LEVEL SECURITY;
ALTER TABLE showings ENABLE ROW LEVEL SECURITY;
ALTER TABLE showings FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_occupancy ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_occupancy FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_holds ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_holds FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_capabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_intake_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_intake_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_seat_uses ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_seat_uses FORCE ROW LEVEL SECURITY;
ALTER TABLE calendar_connections ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_connections FORCE ROW LEVEL SECURITY;
ALTER TABLE calendar_busy ENABLE ROW LEVEL SECURITY;
ALTER TABLE calendar_busy FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_sync ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_sync FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_callbacks ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_callbacks FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_deliveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_deliveries FORCE ROW LEVEL SECURITY;
ALTER TABLE showing_impacts ENABLE ROW LEVEL SECURITY;
ALTER TABLE showing_impacts FORCE ROW LEVEL SECURITY;

CREATE POLICY showing_policies_scope ON showing_policies
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_resources_scope ON showing_resources
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showings_scope ON showings
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_occupancy_scope ON showing_occupancy
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_holds_scope ON showing_holds
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_capabilities_scope ON showing_capabilities
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_intake_keys_scope ON showing_intake_keys
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_seat_uses_scope ON showing_seat_uses
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY calendar_connections_scope ON calendar_connections
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY calendar_busy_scope ON calendar_busy
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_sync_scope ON showing_sync
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_callbacks_scope ON showing_callbacks
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_deliveries_scope ON showing_deliveries
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY showing_impacts_scope ON showing_impacts
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));

GRANT SELECT, INSERT, UPDATE, DELETE ON showing_policies, showing_resources, showings, showing_occupancy, showing_holds,
  showing_capabilities, showing_intake_keys, showing_seat_uses, calendar_connections, calendar_busy, showing_sync,
  showing_callbacks, showing_deliveries, showing_impacts
  TO perchpoint_runtime, perchpoint_definer;

CREATE FUNCTION perchpoint.commit_showing(intake jsonb, idempotency_key text, fingerprint text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  inquiry uuid;
  prospect uuid;
  existing_fp text;
  existing_ref text;
  reference text := replace(gen_random_uuid()::text, '-', '');
  showing uuid := gen_random_uuid();
  host uuid;
  space uuid;
  parent uuid;
  starts timestamptz := (intake->>'starts_at')::timestamptz;
  ends timestamptz := (intake->>'ends_at')::timestamptz;
  mode text := intake->>'mode';
BEGIN
  IF intake ? 'organization_id' OR intake ? 'lead_score' OR intake ? 'access_code' OR intake ? 'lockbox' OR COALESCE(intake->>'mode', '') = 'self_guided' THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  IF mode NOT IN ('individual', 'group', 'remote') OR starts IS NULL OR ends IS NULL OR ends <= starts THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT capability.organization_id, capability.inquiry_id, leasing.prospect_id
    INTO org, inquiry, prospect
  FROM showing_capabilities capability
  JOIN leasing_inquiries leasing ON leasing.organization_id = capability.organization_id AND leasing.id = capability.inquiry_id
  WHERE capability.token_hash = intake->>'capability_hash'
    AND capability.revoked = false
    AND capability.expires_at > now()
    AND capability.purpose = 'book';
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT showing_intake_keys.fingerprint, showing_intake_keys.public_reference INTO existing_fp, existing_ref
  FROM showing_intake_keys
  WHERE organization_id = org AND showing_intake_keys.idempotency_key = commit_showing.idempotency_key;
  IF existing_fp IS NOT NULL THEN
    IF existing_fp <> fingerprint THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
    END IF;
    RETURN jsonb_build_object('accepted', true, 'reference', existing_ref, 'replayed', true);
  END IF;
  host := NULLIF(intake->>'host_resource_id', '')::uuid;
  space := NULLIF(intake->>'space_resource_id', '')::uuid;
  IF host IS NULL THEN
    SELECT id INTO host FROM showing_resources WHERE organization_id = org AND kind = 'host' ORDER BY label LIMIT 1;
  END IF;
  IF space IS NULL THEN
    SELECT id INTO space FROM showing_resources WHERE organization_id = org AND kind = 'space' ORDER BY label LIMIT 1;
  END IF;
  IF host IS NULL OR space IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  INSERT INTO showings (
    organization_id, id, inquiry_id, prospect_id, public_reference, mode, business_state,
    wall_start, zone_name, offset_minutes, starts_at, ends_at, host_resource_id, space_resource_id, guest_count, policy_version
  ) VALUES (
    org, showing, inquiry, prospect, reference, mode, 'confirmed',
    intake->>'wall_start', intake->>'zone_name', (intake->>'offset_minutes')::integer, starts, ends, host, space,
    COALESCE((intake->>'guest_count')::integer, 1), 1
  );
  INSERT INTO showing_occupancy (organization_id, id, resource_id, showing_id, span)
  VALUES
    (org, gen_random_uuid(), host, showing, tstzrange(starts - interval '15 minutes', ends + interval '15 minutes', '[)')),
    (org, gen_random_uuid(), space, showing, tstzrange(starts - interval '15 minutes', ends + interval '15 minutes', '[)'));
  SELECT parent_id INTO parent FROM showing_resources WHERE organization_id = org AND id = space;
  IF parent IS NOT NULL THEN
    INSERT INTO showing_occupancy (organization_id, id, resource_id, showing_id, span)
    VALUES (org, gen_random_uuid(), parent, showing, tstzrange(starts - interval '15 minutes', ends + interval '15 minutes', '[)'));
  END IF;
  IF mode = 'group' THEN
    INSERT INTO showing_seat_uses (organization_id, id, resource_id, showing_id, guests)
    VALUES (org, gen_random_uuid(), space, showing, COALESCE((intake->>'guest_count')::integer, 1));
  END IF;
  INSERT INTO showing_sync (organization_id, showing_id, desired_hash, state)
  VALUES (org, showing, fingerprint, 'pending');
  INSERT INTO showing_deliveries (organization_id, id, showing_id, purpose, state)
  VALUES (org, gen_random_uuid(), showing, 'confirmation', 'sent');
  INSERT INTO showing_intake_keys (organization_id, idempotency_key, fingerprint, public_reference)
  VALUES (org, commit_showing.idempotency_key, fingerprint, reference);
  RETURN jsonb_build_object('accepted', true, 'reference', reference, 'replayed', false, 'zone_name', intake->>'zone_name', 'wall_start', intake->>'wall_start');
END $$;

CREATE FUNCTION perchpoint.issue_showing_capability(receipt text, token_hash text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  inquiry uuid;
  host uuid;
  space uuid;
BEGIN
  SELECT organization_id, id INTO org, inquiry FROM leasing_inquiries WHERE public_receipt = receipt;
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  INSERT INTO showing_policies (organization_id, id)
  SELECT org, gen_random_uuid()
  WHERE NOT EXISTS (SELECT 1 FROM showing_policies WHERE organization_id = org);
  SELECT id INTO host FROM showing_resources WHERE organization_id = org AND kind = 'host' ORDER BY label LIMIT 1;
  IF host IS NULL THEN
    host := gen_random_uuid();
    INSERT INTO showing_resources (organization_id, id, kind, label, capacity) VALUES (org, host, 'host', 'Leasing host', 1);
  END IF;
  SELECT id INTO space FROM showing_resources WHERE organization_id = org AND kind = 'space' ORDER BY label LIMIT 1;
  IF space IS NULL THEN
    space := gen_random_uuid();
    INSERT INTO showing_resources (organization_id, id, kind, label, capacity) VALUES (org, space, 'space', 'Primary space', 1);
  END IF;
  INSERT INTO showing_capabilities (organization_id, token_hash, inquiry_id, purpose, expires_at)
  VALUES (org, token_hash, inquiry, 'book', now() + interval '2 days');
  RETURN jsonb_build_object('accepted', true);
END $$;

CREATE FUNCTION perchpoint.showing_busy(token_hash text, window_start timestamptz, window_end timestamptz)
RETURNS jsonb
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
BEGIN
  SELECT organization_id INTO org FROM showing_capabilities
  WHERE showing_capabilities.token_hash = showing_busy.token_hash AND revoked = false AND expires_at > now();
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  RETURN jsonb_build_object(
    'accepted', true,
    'spans', COALESCE((
      SELECT jsonb_agg(jsonb_build_object('start', lower(span), 'end', upper(span)))
      FROM showing_occupancy
      WHERE organization_id = org AND span && tstzrange(window_start, window_end, '[)')
    ), '[]'::jsonb)
  );
END $$;

REVOKE ALL ON FUNCTION perchpoint.commit_showing(jsonb, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.commit_showing(jsonb, text, text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.issue_showing_capability(text, text) TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.showing_busy(text, timestamptz, timestamptz) TO perchpoint_runtime, perchpoint_definer;
ALTER FUNCTION perchpoint.issue_showing_capability(text, text) OWNER TO perchpoint_definer;

CREATE FUNCTION perchpoint.apply_calendar_callback(reference text, event_id text, change_kind text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  showing uuid;
  business text;
  inserted integer;
BEGIN
  SELECT organization_id, id, business_state INTO org, showing, business
  FROM showings WHERE public_reference = reference;
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  INSERT INTO showing_callbacks (organization_id, provider_event_id, change_kind)
  VALUES (org, event_id, change_kind)
  ON CONFLICT DO NOTHING;
  GET DIAGNOSTICS inserted = ROW_COUNT;
  IF inserted = 0 THEN
    RETURN jsonb_build_object('accepted', true, 'replayed', true, 'business_state', business);
  END IF;
  IF change_kind = 'deleted' THEN
    UPDATE showing_sync SET state = 'drifted', observed_hash = 'deleted'
    WHERE organization_id = org AND showing_id = showing;
  ELSE
    UPDATE showing_sync SET state = 'synced', observed_hash = event_id
    WHERE organization_id = org AND showing_id = showing;
  END IF;
  RETURN jsonb_build_object('accepted', true, 'replayed', false, 'business_state', business, 'sync_state', CASE WHEN change_kind = 'deleted' THEN 'drifted' ELSE 'synced' END);
END $$;

REVOKE ALL ON FUNCTION perchpoint.apply_calendar_callback(text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.apply_calendar_callback(text, text, text) TO perchpoint_runtime, perchpoint_definer;
ALTER FUNCTION perchpoint.apply_calendar_callback(text, text, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.showing_busy(text, timestamptz, timestamptz) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.commit_showing(jsonb, text, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.showing_resource_no_cycle() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.showing_seats_within_capacity() OWNER TO perchpoint_definer;

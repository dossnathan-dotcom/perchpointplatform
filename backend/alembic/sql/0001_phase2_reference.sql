CREATE SCHEMA IF NOT EXISTS perchpoint;

CREATE TABLE organizations (
  id uuid PRIMARY KEY,
  name text NOT NULL,
  synthetic boolean NOT NULL DEFAULT true
);

CREATE TABLE legal_entities (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  legal_name text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (id)
);

CREATE TABLE properties (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  name text NOT NULL,
  property_type text NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  PRIMARY KEY (organization_id, id),
  UNIQUE (id)
);

CREATE TABLE buildings (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  property_id uuid NOT NULL,
  name text NOT NULL,
  allowed_uses text[] NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (id),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id)
);

CREATE TABLE spaces (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  property_id uuid NOT NULL,
  building_id uuid NOT NULL,
  label text NOT NULL,
  use text NOT NULL CHECK (use IN ('residential', 'commercial')),
  square_feet integer NOT NULL CHECK (square_feet > 0),
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  PRIMARY KEY (organization_id, id),
  UNIQUE (id),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id),
  FOREIGN KEY (organization_id, building_id) REFERENCES buildings (organization_id, id)
);

CREATE TABLE ownership_relationships (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  legal_entity_id uuid NOT NULL,
  property_id uuid NOT NULL,
  effective_on date NOT NULL,
  ended_on date,
  CHECK (ended_on IS NULL OR ended_on > effective_on),
  FOREIGN KEY (organization_id, legal_entity_id) REFERENCES legal_entities (organization_id, id),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id)
);

CREATE TABLE management_relationships (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  manager_organization_id uuid NOT NULL REFERENCES organizations(id),
  property_id uuid NOT NULL,
  effective_on date NOT NULL,
  ended_on date,
  CHECK (ended_on IS NULL OR ended_on > effective_on),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties (organization_id, id)
);

CREATE TABLE accounts (
  id uuid PRIMARY KEY,
  email text NOT NULL UNIQUE,
  password_hash text NOT NULL,
  synthetic boolean NOT NULL DEFAULT true
);

CREATE TABLE memberships (
  id uuid PRIMARY KEY,
  account_id uuid NOT NULL REFERENCES accounts(id),
  organization_id uuid NOT NULL REFERENCES organizations(id),
  role_name text NOT NULL,
  effective_at timestamptz NOT NULL,
  ended_at timestamptz,
  CHECK (ended_at IS NULL OR ended_at > effective_at)
);

CREATE TABLE households (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  label text NOT NULL,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE portal_access (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  household_id uuid NOT NULL,
  account_id uuid NOT NULL REFERENCES accounts(id),
  kind text NOT NULL CHECK (kind IN ('primary', 'additional')),
  effective_at timestamptz NOT NULL,
  ended_at timestamptz,
  CHECK (ended_at IS NULL OR ended_at > effective_at),
  FOREIGN KEY (organization_id, household_id) REFERENCES households (organization_id, id)
);

CREATE UNIQUE INDEX one_open_primary_portal
  ON portal_access (organization_id, household_id)
  WHERE kind = 'primary' AND ended_at IS NULL;

CREATE TABLE space_states (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  space_id uuid NOT NULL,
  condition text NOT NULL,
  occupancy text NOT NULL,
  availability text NOT NULL,
  publication text NOT NULL,
  maintenance_restriction text NOT NULL,
  legal_restriction text NOT NULL,
  version integer NOT NULL CHECK (version >= 1),
  current boolean NOT NULL DEFAULT true,
  CHECK (publication <> 'published' OR (availability = 'offerable' AND legal_restriction = 'none')),
  CHECK (occupancy <> 'occupied' OR availability <> 'offerable'),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE UNIQUE INDEX one_current_space_state
  ON space_states (organization_id, space_id)
  WHERE current;

CREATE TABLE listings (
  organization_id uuid NOT NULL,
  id uuid PRIMARY KEY,
  space_id uuid NOT NULL,
  publication text NOT NULL,
  availability text NOT NULL,
  property_name text NOT NULL,
  label text NOT NULL,
  use text NOT NULL,
  municipality text NOT NULL,
  state text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor >= 0),
  currency text NOT NULL CHECK (currency ~ '^[A-Z]{3}$'),
  FOREIGN KEY (organization_id, space_id) REFERENCES spaces (organization_id, id)
);

CREATE TABLE inquiries (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  listing_id uuid NOT NULL REFERENCES listings(id),
  name text NOT NULL,
  email text NOT NULL,
  intent text NOT NULL,
  message text NOT NULL,
  status text NOT NULL,
  assigned_account_id uuid,
  version integer NOT NULL CHECK (version >= 1),
  received_at timestamptz NOT NULL
);

CREATE TABLE activity (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  resource_type text NOT NULL,
  resource_id uuid NOT NULL,
  summary text NOT NULL,
  occurred_at timestamptz NOT NULL,
  actor_id uuid
);

CREATE TABLE audit_events (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  actor_id uuid,
  action text NOT NULL,
  resource_type text NOT NULL,
  resource_id uuid NOT NULL,
  occurred_at timestamptz NOT NULL,
  correlation_id uuid NOT NULL,
  result text NOT NULL,
  previous_event_hash text,
  event_hash text NOT NULL,
  redacted boolean NOT NULL DEFAULT true
);

CREATE TABLE outbox (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  event_type text NOT NULL,
  aggregate_id uuid NOT NULL,
  payload jsonb NOT NULL,
  status text NOT NULL,
  attempts integer NOT NULL DEFAULT 0,
  claimed_by text,
  lease_until timestamptz,
  available_at timestamptz NOT NULL,
  last_error text
);

CREATE TABLE inbox (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid PRIMARY KEY,
  provider text NOT NULL,
  account_name text NOT NULL,
  environment text NOT NULL,
  provider_event_id text NOT NULL,
  payload jsonb NOT NULL,
  disposition text NOT NULL,
  received_at timestamptz NOT NULL,
  UNIQUE (provider, account_name, environment, provider_event_id)
);

CREATE TABLE idempotency_keys (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  result jsonb NOT NULL,
  created_at timestamptz NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE OR REPLACE FUNCTION perchpoint.current_org() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.organization_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION perchpoint.current_actor() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT NULLIF(current_setting('app.actor_id', true), '')::uuid
$$;

CREATE OR REPLACE FUNCTION perchpoint.actor_in_org(target uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1 FROM memberships m
    WHERE m.account_id = perchpoint.current_actor()
      AND m.organization_id = target
      AND m.effective_at <= now()
      AND (m.ended_at IS NULL OR m.ended_at > now())
  )
$$;

CREATE OR REPLACE FUNCTION perchpoint.login_material(lookup text)
RETURNS TABLE (id uuid, password_hash text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT id, password_hash FROM accounts WHERE email = lookup
$$;

CREATE OR REPLACE FUNCTION perchpoint.published_listings()
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
  currency text
)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT id, space_id, property_name, label, use, municipality, state, publication, availability, amount_minor, currency
  FROM listings
  WHERE publication = 'published' AND availability = 'offerable' AND currency = 'USD'
$$;

CREATE OR REPLACE FUNCTION perchpoint.current_membership(account uuid)
RETURNS TABLE (organization_id uuid, role_name text)
LANGUAGE sql STABLE SECURITY DEFINER
SET search_path = public, pg_temp AS $$
  SELECT organization_id, role_name FROM memberships
  WHERE account_id = account AND effective_at <= now() AND (ended_at IS NULL OR ended_at > now())
  ORDER BY effective_at DESC
  LIMIT 1
$$;

CREATE OR REPLACE FUNCTION perchpoint.submit_public_inquiry(
  listing uuid, inquiry_name text, inquiry_email text, inquiry_intent text, inquiry_message text,
  idem_key text, request_fingerprint text, correlation uuid
)
RETURNS TABLE (inquiry_id uuid, status text, correlation_id uuid, conflict boolean)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  existing_fp text;
  existing jsonb;
  new_id uuid;
BEGIN
  SELECT organization_id INTO org FROM listings
  WHERE id = listing AND publication = 'published' AND availability = 'offerable';
  IF org IS NULL THEN
    RAISE EXCEPTION 'published listing was not found' USING ERRCODE = 'P0002';
  END IF;
  SELECT fingerprint, result INTO existing_fp, existing
  FROM idempotency_keys WHERE organization_id = org AND idempotency_key = idem_key;
  IF FOUND THEN
    IF existing_fp <> request_fingerprint THEN
      inquiry_id := NULL; status := 'conflict'; correlation_id := correlation; conflict := true;
      RETURN NEXT;
      RETURN;
    END IF;
    inquiry_id := (existing->>'inquiry_id')::uuid;
    status := existing->>'status';
    correlation_id := (existing->>'correlation_id')::uuid;
    conflict := false;
    RETURN NEXT;
    RETURN;
  END IF;
  new_id := gen_random_uuid();
  INSERT INTO inquiries (organization_id, id, listing_id, name, email, intent, message, status, version, received_at)
  VALUES (org, new_id, listing, inquiry_name, inquiry_email, inquiry_intent, inquiry_message, 'new', 1, now());
  INSERT INTO idempotency_keys (organization_id, idempotency_key, fingerprint, result, created_at)
  VALUES (org, idem_key, request_fingerprint, jsonb_build_object('inquiry_id', new_id, 'status', 'received', 'correlation_id', correlation), now());
  inquiry_id := new_id; status := 'received'; correlation_id := correlation; conflict := false;
  RETURN NEXT;
END;
$$;

CREATE OR REPLACE FUNCTION perchpoint.claim_outbox(worker text)
RETURNS TABLE (id uuid, organization_id uuid, attempts integer)
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp AS $$
DECLARE claimed record;
BEGIN
  SELECT o.id, o.organization_id, o.attempts INTO claimed
  FROM outbox o
  WHERE o.status IN ('pending', 'claimed')
    AND o.available_at <= now()
    AND (o.lease_until IS NULL OR o.lease_until < now())
  ORDER BY o.available_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN
    RETURN;
  END IF;
  IF claimed.attempts >= 5 THEN
    UPDATE outbox SET status = 'dead_letter', last_error = 'attempt limit' WHERE outbox.id = claimed.id;
    RETURN QUERY SELECT claimed.id, claimed.organization_id, claimed.attempts;
    RETURN;
  END IF;
  UPDATE outbox
    SET status = 'claimed', claimed_by = worker, lease_until = now() + interval '30 seconds', attempts = attempts + 1
    WHERE outbox.id = claimed.id;
  RETURN QUERY SELECT claimed.id, claimed.organization_id, claimed.attempts + 1;
END;
$$;

CREATE OR REPLACE FUNCTION perchpoint.finish_outbox(target uuid, delivered boolean)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER
SET search_path = public, pg_temp AS $$
BEGIN
  IF delivered THEN
    UPDATE outbox SET status = 'delivered', lease_until = NULL WHERE id = target AND status = 'claimed';
    RETURN 'delivered';
  END IF;
  UPDATE outbox
    SET status = 'pending', available_at = now() + interval '1 second', last_error = 'synthetic rejection', lease_until = NULL
    WHERE id = target AND status = 'claimed';
  RETURN 'retry';
END;
$$;

CREATE OR REPLACE FUNCTION perchpoint.reject_audit_mutation() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  RAISE EXCEPTION 'audit events are append-only';
END;
$$;

CREATE TRIGGER audit_no_update BEFORE UPDATE OR DELETE ON audit_events
FOR EACH ROW EXECUTE FUNCTION perchpoint.reject_audit_mutation();

ALTER TABLE organizations ENABLE ROW LEVEL SECURITY;
ALTER TABLE organizations FORCE ROW LEVEL SECURITY;
CREATE POLICY org_self ON organizations
  USING (id = perchpoint.current_org() AND perchpoint.actor_in_org(id))
  WITH CHECK (id = perchpoint.current_org() AND perchpoint.actor_in_org(id));

DO $$
DECLARE tbl text;
BEGIN
  FOREACH tbl IN ARRAY ARRAY[
    'legal_entities','properties','buildings','spaces','ownership_relationships',
    'management_relationships','memberships','households','portal_access','space_states',
    'listings','inquiries','activity','audit_events','outbox','inbox','idempotency_keys'
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

ALTER TABLE accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounts FORCE ROW LEVEL SECURITY;
CREATE POLICY account_self ON accounts
  USING (id = perchpoint.current_actor())
  WITH CHECK (false);

REVOKE ALL ON FUNCTION perchpoint.current_org() FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.current_actor() FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.actor_in_org(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.current_membership(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.submit_public_inquiry(uuid, text, text, text, text, text, text, uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.claim_outbox(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.finish_outbox(uuid, boolean) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.login_material(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.published_listings() FROM PUBLIC;

GRANT USAGE ON SCHEMA perchpoint TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.current_org() TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.current_actor() TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.actor_in_org(uuid) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.current_membership(uuid) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.submit_public_inquiry(uuid, text, text, text, text, text, text, uuid) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.claim_outbox(text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.finish_outbox(uuid, boolean) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.login_material(text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.published_listings() TO perchpoint_runtime;

GRANT SELECT, INSERT, UPDATE ON
  organizations, legal_entities, properties, buildings, spaces, ownership_relationships,
  management_relationships, memberships, households, portal_access, space_states,
  listings, inquiries, activity, outbox, inbox, idempotency_keys
TO perchpoint_runtime;
GRANT SELECT ON accounts TO perchpoint_runtime;
GRANT SELECT, INSERT ON audit_events TO perchpoint_runtime;

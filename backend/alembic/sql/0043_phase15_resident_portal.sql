-- Phase 15 consumes a Phase 14 activation. It does not post a ledger, collect money,
-- create a maintenance case, or claim a message was delivered.

CREATE TABLE portal_memberships (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  deal_id uuid NOT NULL,
  public_reference text NOT NULL,
  role_name text NOT NULL CHECK (role_name IN ('leaseholder', 'co_resident', 'occupant', 'former')),
  state text NOT NULL CHECK (state IN ('pending', 'active', 'revoked', 'former')),
  person_label text NOT NULL,
  version integer NOT NULL DEFAULT 1 CHECK (version >= 1),
  PRIMARY KEY (organization_id, id),
  UNIQUE (public_reference),
  FOREIGN KEY (organization_id, deal_id) REFERENCES lease_deals (organization_id, id)
);

CREATE UNIQUE INDEX portal_one_open_membership
  ON portal_memberships (organization_id, deal_id, role_name)
  WHERE state <> 'revoked';

CREATE TABLE portal_invitations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  token_hash text NOT NULL,
  purpose text NOT NULL CHECK (purpose = 'household_access'),
  state text NOT NULL CHECK (state IN ('issued', 'accepted', 'revoked', 'expired')),
  expires_at timestamptz NOT NULL,
  attempts integer NOT NULL DEFAULT 0 CHECK (attempts >= 0),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, token_hash),
  FOREIGN KEY (organization_id, membership_id) REFERENCES portal_memberships (organization_id, id)
);

CREATE TABLE portal_intake_keys (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE TABLE portal_documents (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  artifact_code text NOT NULL,
  content_hash text NOT NULL,
  body text NOT NULL,
  sample_marker text NOT NULL,
  superseded boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, membership_id) REFERENCES portal_memberships (organization_id, id),
  CHECK (position('SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION' in body) > 0),
  CHECK (sample_marker = 'SAMPLE — NOT A REAL LEASE — NOT FOR EXECUTION')
);

CREATE TABLE portal_entitlements (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  document_id uuid NOT NULL,
  state text NOT NULL CHECK (state IN ('current', 'retained', 'revoked')),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, membership_id, document_id),
  FOREIGN KEY (organization_id, membership_id) REFERENCES portal_memberships (organization_id, id),
  FOREIGN KEY (organization_id, document_id) REFERENCES portal_documents (organization_id, id)
);

CREATE TABLE portal_preferences (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  version integer NOT NULL CHECK (version >= 1),
  channel text NOT NULL,
  quiet_hours boolean NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, membership_id, version),
  FOREIGN KEY (organization_id, membership_id) REFERENCES portal_memberships (organization_id, id)
);

CREATE TABLE portal_requests (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  request_kind text NOT NULL CHECK (request_kind IN ('profile', 'access', 'accommodation')),
  state text NOT NULL CHECK (state IN ('submitted', 'withdrawn', 'approved', 'denied')),
  requested_delta text NOT NULL,
  sensitive boolean NOT NULL DEFAULT false,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, membership_id) REFERENCES portal_memberships (organization_id, id)
);

CREATE TABLE portal_activity (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  action_code text NOT NULL,
  safe_label text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, membership_id) REFERENCES portal_memberships (organization_id, id)
);

CREATE TABLE portal_notices (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  audience text NOT NULL,
  body text NOT NULL,
  state text NOT NULL CHECK (state IN ('draft', 'published')),
  version integer NOT NULL CHECK (version >= 1),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE portal_config_versions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  family_code text NOT NULL,
  version integer NOT NULL CHECK (version >= 1),
  state text NOT NULL CHECK (state = 'published'),
  content_hash text NOT NULL,
  clause_code text NOT NULL,
  human_confirmed boolean NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, family_code, version),
  CHECK (human_confirmed),
  CHECK (clause_code <> '')
);

CREATE TABLE portal_outbox (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  event_code text NOT NULL,
  delivery_state text NOT NULL CHECK (delivery_state IN ('queued', 'accepted_locally', 'failed')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, membership_id) REFERENCES portal_memberships (organization_id, id)
);

CREATE TABLE portal_manifest_runs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  manifest_version integer NOT NULL CHECK (manifest_version >= 1),
  dry_run boolean NOT NULL,
  real_values_activated boolean NOT NULL,
  PRIMARY KEY (organization_id, id),
  CHECK (dry_run),
  CHECK (real_values_activated = false)
);

CREATE INDEX portal_memberships_queue ON portal_memberships (organization_id, state, public_reference);
CREATE INDEX portal_documents_membership ON portal_documents (organization_id, membership_id);
CREATE INDEX portal_activity_membership ON portal_activity (organization_id, membership_id);
CREATE INDEX portal_requests_membership ON portal_requests (organization_id, membership_id, state);
CREATE INDEX portal_invitations_membership ON portal_invitations (organization_id, membership_id, state);

ALTER TABLE portal_memberships ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_memberships FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_invitations FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_intake_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_intake_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_documents FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_entitlements ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_entitlements FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_preferences ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_preferences FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_requests FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_activity ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_activity FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_notices FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_config_versions ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_config_versions FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_outbox ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_outbox FORCE ROW LEVEL SECURITY;
ALTER TABLE portal_manifest_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE portal_manifest_runs FORCE ROW LEVEL SECURITY;

CREATE POLICY portal_memberships_scope ON portal_memberships
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_invitations_scope ON portal_invitations
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_intake_keys_scope ON portal_intake_keys
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_documents_scope ON portal_documents
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_entitlements_scope ON portal_entitlements
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_preferences_scope ON portal_preferences
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_requests_scope ON portal_requests
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_activity_scope ON portal_activity
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_notices_scope ON portal_notices
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_config_versions_scope ON portal_config_versions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_outbox_scope ON portal_outbox
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY portal_manifest_runs_scope ON portal_manifest_runs
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));

GRANT SELECT, INSERT, UPDATE, DELETE ON portal_memberships, portal_invitations, portal_intake_keys,
  portal_documents, portal_entitlements, portal_preferences, portal_requests, portal_activity,
  portal_notices, portal_config_versions, portal_outbox, portal_manifest_runs
  TO perchpoint_runtime, perchpoint_definer;

CREATE FUNCTION perchpoint.accept_portal_invitation(token_hash text, idempotency_key text, fingerprint text)
RETURNS jsonb
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  org uuid;
  membership uuid;
  invitation uuid;
  current_state text;
  expiry timestamptz;
  existing_fp text;
  reference text;
BEGIN
  SELECT invitation_row.organization_id, invitation_row.membership_id, invitation_row.id,
         invitation_row.state, invitation_row.expires_at
    INTO org, membership, invitation, current_state, expiry
  FROM portal_invitations invitation_row
  WHERE invitation_row.token_hash = accept_portal_invitation.token_hash;
  IF org IS NULL THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  PERFORM pg_advisory_xact_lock(hashtext(org::text || membership::text));
  SELECT intake.fingerprint INTO existing_fp
  FROM portal_intake_keys intake
  WHERE intake.organization_id = org AND intake.idempotency_key = accept_portal_invitation.idempotency_key;
  IF existing_fp IS NOT NULL THEN
    IF existing_fp <> fingerprint THEN
      RETURN jsonb_build_object('accepted', false, 'code', 'conflict');
    END IF;
    RETURN jsonb_build_object('accepted', true, 'replayed', true, 'state', 'active');
  END IF;
  IF current_state <> 'issued' OR expiry <= now() THEN
    RETURN jsonb_build_object('accepted', false, 'code', 'rejected');
  END IF;
  SELECT public_reference INTO reference FROM portal_memberships
  WHERE organization_id = org AND id = membership FOR UPDATE;
  UPDATE portal_invitations SET state = 'accepted', attempts = attempts + 1
  WHERE organization_id = org AND id = invitation AND state = 'issued';
  UPDATE portal_memberships SET state = 'active', version = version + 1
  WHERE organization_id = org AND id = membership AND state = 'pending';
  INSERT INTO portal_intake_keys (organization_id, idempotency_key, fingerprint, public_reference)
  VALUES (org, accept_portal_invitation.idempotency_key, fingerprint, reference);
  INSERT INTO portal_activity (organization_id, id, membership_id, action_code, safe_label)
  VALUES (org, gen_random_uuid(), membership, 'invitation.accepted', 'Household access accepted');
  INSERT INTO portal_outbox (organization_id, id, membership_id, event_code, delivery_state)
  VALUES (org, gen_random_uuid(), membership, 'invitation.accepted', 'accepted_locally');
  RETURN jsonb_build_object('accepted', true, 'replayed', false, 'state', 'active', 'reference', reference);
END $$;

REVOKE ALL ON FUNCTION perchpoint.accept_portal_invitation(text, text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.accept_portal_invitation(text, text, text) TO perchpoint_runtime, perchpoint_definer;
ALTER FUNCTION perchpoint.accept_portal_invitation(text, text, text) OWNER TO perchpoint_definer;

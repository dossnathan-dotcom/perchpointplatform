DELETE FROM identity_factors;
ALTER TABLE identity_factors DROP COLUMN secret_ciphertext;
ALTER TABLE identity_factors ADD COLUMN provider_factor_id text;

ALTER TABLE identity_sessions ADD COLUMN provider_session_id text;
ALTER TABLE identity_sessions ADD COLUMN refresh_ciphertext text;
ALTER TABLE identity_sessions ADD COLUMN idle_window interval NOT NULL DEFAULT interval '1 hour';
ALTER TABLE identity_sessions ADD COLUMN context_membership uuid;

ALTER TABLE delegations ADD COLUMN decision_type text;
ALTER TABLE delegations ADD COLUMN resource_type text;
ALTER TABLE delegations ADD COLUMN resource_id uuid;
ALTER TABLE delegations ADD COLUMN policy_version text NOT NULL DEFAULT 'phase6-1';
ALTER TABLE delegations ADD COLUMN approved_by uuid;
ALTER TABLE delegations ADD COLUMN revoked_at timestamptz;
ALTER TABLE delegations DROP CONSTRAINT IF EXISTS delegations_no_self_approval;
ALTER TABLE delegations ADD CONSTRAINT delegations_no_self_approval CHECK (approved_by IS NULL OR (approved_by <> grantor_id AND approved_by <> grantee_id));

CREATE TABLE capabilities (
  code text PRIMARY KEY,
  family text NOT NULL,
  description text NOT NULL
);

CREATE TABLE role_bundles (
  id uuid PRIMARY KEY,
  name text NOT NULL UNIQUE,
  version integer NOT NULL CHECK (version > 0),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE role_bundle_capabilities (
  bundle_id uuid NOT NULL REFERENCES role_bundles(id),
  capability text NOT NULL REFERENCES capabilities(code),
  PRIMARY KEY (bundle_id, capability)
);

CREATE TABLE authorization_scopes (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  scope_type text NOT NULL,
  resource_id uuid,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE membership_scope_assignments (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  scope_id uuid NOT NULL,
  effective_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  PRIMARY KEY (organization_id, id),
  CHECK (ended_at IS NULL OR ended_at > effective_at)
);

CREATE TABLE service_credentials (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  principal_id uuid NOT NULL,
  verifier_hash text NOT NULL,
  expires_at timestamptz NOT NULL,
  revoked_at timestamptz,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE privileged_recoveries (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  subject_account uuid NOT NULL,
  initiator_account uuid NOT NULL,
  approver_account uuid,
  status text NOT NULL CHECK (status IN ('waiting', 'ready', 'completed', 'denied')),
  not_before timestamptz NOT NULL,
  evidence_note text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  CHECK (initiator_account <> subject_account),
  CHECK (approver_account IS NULL OR approver_account <> subject_account)
);

CREATE TABLE access_review_campaigns (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  title text NOT NULL,
  opens_at timestamptz NOT NULL,
  due_at timestamptz NOT NULL,
  PRIMARY KEY (organization_id, id),
  CHECK (due_at > opens_at)
);

CREATE TABLE access_review_items (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  campaign_id uuid NOT NULL,
  account_id uuid NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'certified', 'revoked')),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE auth_attempts (
  id uuid PRIMARY KEY,
  subject_key text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE capabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE role_bundles ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_bundles FORCE ROW LEVEL SECURITY;
ALTER TABLE role_bundle_capabilities ENABLE ROW LEVEL SECURITY;
ALTER TABLE role_bundle_capabilities FORCE ROW LEVEL SECURITY;
ALTER TABLE authorization_scopes ENABLE ROW LEVEL SECURITY;
ALTER TABLE authorization_scopes FORCE ROW LEVEL SECURITY;
ALTER TABLE membership_scope_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE membership_scope_assignments FORCE ROW LEVEL SECURITY;
ALTER TABLE service_credentials ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_credentials FORCE ROW LEVEL SECURITY;
ALTER TABLE privileged_recoveries ENABLE ROW LEVEL SECURITY;
ALTER TABLE privileged_recoveries FORCE ROW LEVEL SECURITY;
ALTER TABLE access_review_campaigns ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_review_campaigns FORCE ROW LEVEL SECURITY;
ALTER TABLE access_review_items ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_review_items FORCE ROW LEVEL SECURITY;
ALTER TABLE auth_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE auth_attempts FORCE ROW LEVEL SECURITY;

CREATE POLICY capability_read ON capabilities FOR SELECT USING (perchpoint.current_actor() IS NOT NULL);
CREATE POLICY bundle_read ON role_bundles FOR SELECT USING (perchpoint.current_actor() IS NOT NULL);
CREATE POLICY bundle_capability_read ON role_bundle_capabilities FOR SELECT USING (perchpoint.current_actor() IS NOT NULL);
CREATE POLICY scope_org ON authorization_scopes
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));
CREATE POLICY scope_assignment_org ON membership_scope_assignments
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));
CREATE POLICY service_credential_org ON service_credentials
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));
CREATE POLICY recovery_org ON privileged_recoveries
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));
CREATE POLICY review_campaign_org ON access_review_campaigns
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));
CREATE POLICY review_item_org ON access_review_items
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));

GRANT SELECT ON capabilities, role_bundles, role_bundle_capabilities TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT, UPDATE, DELETE ON authorization_scopes, membership_scope_assignments, service_credentials,
  privileged_recoveries, access_review_campaigns, access_review_items TO perchpoint_runtime, perchpoint_definer;

DROP FUNCTION perchpoint.resolve_session(text);
CREATE FUNCTION perchpoint.resolve_session(token_hash text)
RETURNS TABLE (
  session_id uuid, account_id uuid, organization_id uuid, assurance text,
  idle_expires_at timestamptz, absolute_expires_at timestamptz, revoked_at timestamptz,
  reauthenticated_at timestamptz, csrf_hash text, refresh_ciphertext text, provider_session_id text,
  context_membership uuid, status text
)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  UPDATE identity_sessions AS session_row
  SET last_seen_at = now(),
      idle_expires_at = LEAST(session_row.absolute_expires_at, now() + session_row.idle_window)
  WHERE session_row.token_hash = resolve_session.token_hash
    AND session_row.revoked_at IS NULL
    AND session_row.idle_expires_at > now()
    AND session_row.absolute_expires_at > now();
  RETURN QUERY
  SELECT s.id, a.account_id, s.organization_id, s.assurance, s.idle_expires_at, s.absolute_expires_at,
         s.revoked_at, s.reauthenticated_at, s.csrf_hash, s.refresh_ciphertext, s.provider_session_id,
         s.context_membership, a.status
  FROM identity_sessions s
  JOIN identity_accounts a ON a.id = s.identity_id
  WHERE s.token_hash = resolve_session.token_hash;
END;
$$;

CREATE FUNCTION perchpoint.record_provider_session(
  account uuid, subject text, org uuid, token_hash text, csrf_hash text,
  assurance text, device text, idle_until timestamptz, absolute_until timestamptz,
  idle_seconds integer, provider_session text, refresh_ciphertext text
) RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE
  identity uuid;
  session_id uuid := gen_random_uuid();
BEGIN
  SELECT id INTO identity FROM identity_accounts WHERE account_id = account;
  IF identity IS NULL THEN
    identity := gen_random_uuid();
    INSERT INTO identity_accounts (id, account_id, provider_subject, status, email_verified, assurance)
    VALUES (identity, account, subject, 'active', true, assurance);
  ELSE
    IF EXISTS (
      SELECT 1 FROM identity_accounts
      WHERE id = identity AND provider_subject <> subject AND provider_subject NOT LIKE 'local:%'
    ) THEN
      RAISE EXCEPTION 'provider subject mismatch' USING ERRCODE = '42501';
    END IF;
    UPDATE identity_accounts SET provider_subject = subject WHERE id = identity;
  END IF;
  INSERT INTO identity_sessions (
    id, identity_id, organization_id, token_hash, csrf_hash, assurance, device_label,
    idle_expires_at, absolute_expires_at, reauthenticated_at, idle_window, provider_session_id, refresh_ciphertext
  ) VALUES (
    session_id, identity, org, token_hash, csrf_hash, assurance, device,
    idle_until, absolute_until, now(), make_interval(secs => idle_seconds), provider_session, refresh_ciphertext
  );
  RETURN session_id;
END;
$$;

CREATE FUNCTION perchpoint.account_id_for_email(lookup text)
RETURNS uuid
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT id FROM accounts WHERE email = lookup
$$;

CREATE FUNCTION perchpoint.note_auth_attempt(subject_key text)
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE recent integer;
BEGIN
  INSERT INTO auth_attempts (id, subject_key) VALUES (gen_random_uuid(), subject_key);
  SELECT count(*) INTO recent FROM auth_attempts
  WHERE auth_attempts.subject_key = note_auth_attempt.subject_key
    AND created_at > now() - interval '15 minutes';
  RETURN recent;
END;
$$;

CREATE FUNCTION perchpoint.list_memberships(account uuid)
RETURNS TABLE (membership_id uuid, organization_id uuid, role_name text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT id, organization_id, role_name FROM memberships
  WHERE account_id = account AND effective_at <= now() AND (ended_at IS NULL OR ended_at > now())
  ORDER BY effective_at DESC
$$;

REVOKE ALL ON FUNCTION perchpoint.resolve_session(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.record_provider_session(uuid, text, uuid, text, text, text, text, timestamp with time zone, timestamp with time zone, integer, text, text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.account_id_for_email(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.note_auth_attempt(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.list_memberships(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.resolve_session(text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.record_provider_session(uuid, text, uuid, text, text, text, text, timestamp with time zone, timestamp with time zone, integer, text, text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.account_id_for_email(text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.note_auth_attempt(text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.list_memberships(uuid) TO perchpoint_runtime;

CREATE FUNCTION perchpoint.revoke_account_sessions(account uuid, reason text)
RETURNS void
LANGUAGE sql SECURITY DEFINER SET search_path = public, pg_temp AS $$
  UPDATE identity_sessions
  SET revoked_at = now(), revoke_reason = reason
  WHERE revoked_at IS NULL
    AND identity_id IN (SELECT id FROM identity_accounts WHERE account_id = account)
$$;

REVOKE ALL ON FUNCTION perchpoint.revoke_account_sessions(uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.revoke_account_sessions(uuid, text) TO perchpoint_runtime;

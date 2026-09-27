CREATE TABLE identity_accounts (
  id uuid PRIMARY KEY,
  account_id uuid NOT NULL UNIQUE REFERENCES accounts(id),
  provider_subject text NOT NULL UNIQUE,
  status text NOT NULL CHECK (status IN ('active', 'suspended', 'closed')),
  email_verified boolean NOT NULL DEFAULT false,
  assurance text NOT NULL DEFAULT 'aal1' CHECK (assurance IN ('aal1', 'aal2')),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE identity_sessions (
  id uuid PRIMARY KEY,
  identity_id uuid NOT NULL REFERENCES identity_accounts(id),
  organization_id uuid NOT NULL REFERENCES organizations(id),
  token_hash text NOT NULL UNIQUE,
  csrf_hash text NOT NULL,
  assurance text NOT NULL CHECK (assurance IN ('aal1', 'aal2')),
  device_label text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  last_seen_at timestamptz NOT NULL DEFAULT now(),
  idle_expires_at timestamptz NOT NULL,
  absolute_expires_at timestamptz NOT NULL,
  reauthenticated_at timestamptz,
  revoked_at timestamptz,
  revoke_reason text
);

CREATE TABLE identity_factors (
  id uuid PRIMARY KEY,
  identity_id uuid NOT NULL REFERENCES identity_accounts(id),
  kind text NOT NULL CHECK (kind IN ('totp')),
  secret_ciphertext text NOT NULL,
  confirmed_at timestamptz,
  removed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE identity_recovery_codes (
  id uuid PRIMARY KEY,
  identity_id uuid NOT NULL REFERENCES identity_accounts(id),
  code_hash text NOT NULL,
  used_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE identity_invitations (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  PRIMARY KEY (organization_id, id),
  email text NOT NULL,
  token_hash text NOT NULL UNIQUE,
  role_name text NOT NULL,
  purpose text NOT NULL,
  inviter_id uuid NOT NULL,
  expires_at timestamptz NOT NULL,
  accepted_at timestamptz,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (expires_at > created_at)
);

CREATE TABLE delegations (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  PRIMARY KEY (organization_id, id),
  grantor_id uuid NOT NULL,
  grantee_id uuid NOT NULL,
  capability text NOT NULL,
  amount_ceiling_minor integer CHECK (amount_ceiling_minor IS NULL OR amount_ceiling_minor >= 0),
  currency text NOT NULL DEFAULT 'USD',
  starts_at timestamptz NOT NULL DEFAULT now(),
  ends_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
  reason text NOT NULL,
  derived_from uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (grantor_id <> grantee_id),
  CHECK (ends_at > starts_at),
  CHECK (derived_from IS NULL)
);

CREATE TABLE access_requests (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  PRIMARY KEY (organization_id, id),
  requester_id uuid NOT NULL,
  capability text NOT NULL,
  justification text NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'approved', 'denied', 'expired')),
  approver_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  CHECK (approver_id IS NULL OR approver_id <> requester_id)
);

CREATE TABLE service_principals (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  PRIMARY KEY (organization_id, id),
  name text NOT NULL,
  status text NOT NULL CHECK (status IN ('active', 'revoked')),
  credential_hash text,
  interactive boolean NOT NULL DEFAULT false,
  expires_at timestamptz,
  CHECK (interactive = false)
);

CREATE TABLE security_events (
  id uuid PRIMARY KEY,
  organization_id uuid,
  identity_id uuid,
  action text NOT NULL,
  outcome text NOT NULL,
  correlation_id uuid NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE identity_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE identity_sessions ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_sessions FORCE ROW LEVEL SECURITY;
ALTER TABLE identity_factors ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_factors FORCE ROW LEVEL SECURITY;
ALTER TABLE identity_recovery_codes ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_recovery_codes FORCE ROW LEVEL SECURITY;
ALTER TABLE identity_invitations ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_invitations FORCE ROW LEVEL SECURITY;
ALTER TABLE delegations ENABLE ROW LEVEL SECURITY;
ALTER TABLE delegations FORCE ROW LEVEL SECURITY;
ALTER TABLE access_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_requests FORCE ROW LEVEL SECURITY;
ALTER TABLE service_principals ENABLE ROW LEVEL SECURITY;
ALTER TABLE service_principals FORCE ROW LEVEL SECURITY;
ALTER TABLE security_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE security_events FORCE ROW LEVEL SECURITY;

CREATE POLICY identity_account_self ON identity_accounts
  USING (account_id = perchpoint.current_actor())
  WITH CHECK (account_id = perchpoint.current_actor());

CREATE POLICY identity_session_self ON identity_sessions
  USING (identity_id IN (SELECT id FROM identity_accounts WHERE account_id = perchpoint.current_actor()))
  WITH CHECK (identity_id IN (SELECT id FROM identity_accounts WHERE account_id = perchpoint.current_actor()));

CREATE POLICY identity_factor_self ON identity_factors
  USING (identity_id IN (SELECT id FROM identity_accounts WHERE account_id = perchpoint.current_actor()))
  WITH CHECK (identity_id IN (SELECT id FROM identity_accounts WHERE account_id = perchpoint.current_actor()));

CREATE POLICY identity_recovery_self ON identity_recovery_codes
  USING (identity_id IN (SELECT id FROM identity_accounts WHERE account_id = perchpoint.current_actor()))
  WITH CHECK (identity_id IN (SELECT id FROM identity_accounts WHERE account_id = perchpoint.current_actor()));

CREATE POLICY invitation_org ON identity_invitations
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));

CREATE POLICY delegation_org ON delegations
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));

CREATE POLICY access_request_org ON access_requests
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));

CREATE POLICY service_principal_org ON service_principals
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));

CREATE POLICY security_event_insert ON security_events
  FOR INSERT WITH CHECK (true);
CREATE POLICY security_event_read ON security_events
  FOR SELECT USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));

REVOKE UPDATE, DELETE ON security_events FROM perchpoint_runtime;

CREATE OR REPLACE FUNCTION perchpoint.resolve_session(token_hash text)
RETURNS TABLE (session_id uuid, account_id uuid, organization_id uuid, assurance text, idle_expires_at timestamptz, absolute_expires_at timestamptz, revoked_at timestamptz, reauthenticated_at timestamptz, csrf_hash text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT s.id, a.account_id, s.organization_id, s.assurance, s.idle_expires_at, s.absolute_expires_at, s.revoked_at, s.reauthenticated_at, s.csrf_hash
  FROM identity_sessions s
  JOIN identity_accounts a ON a.id = s.identity_id
  WHERE s.token_hash = resolve_session.token_hash
$$;

REVOKE ALL ON FUNCTION perchpoint.resolve_session(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.resolve_session(text) TO perchpoint_runtime;

CREATE OR REPLACE FUNCTION perchpoint.record_session(
  account uuid, subject text, org uuid, token_hash text, csrf_hash text,
  assurance text, device text, idle_until timestamptz, absolute_until timestamptz
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
  END IF;
  INSERT INTO identity_sessions (
    id, identity_id, organization_id, token_hash, csrf_hash, assurance, device_label, idle_expires_at, absolute_expires_at, reauthenticated_at
  ) VALUES (
    session_id, identity, org, token_hash, csrf_hash, assurance, device, idle_until, absolute_until, now()
  );
  RETURN session_id;
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.record_session(uuid, text, uuid, text, text, text, text, timestamptz, timestamptz) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.record_session(uuid, text, uuid, text, text, text, text, timestamptz, timestamptz) TO perchpoint_runtime;

GRANT SELECT, INSERT, UPDATE, DELETE ON identity_accounts, identity_sessions, identity_factors, identity_recovery_codes,
  identity_invitations, delegations, access_requests, service_principals TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON security_events TO perchpoint_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON security_events TO perchpoint_definer;

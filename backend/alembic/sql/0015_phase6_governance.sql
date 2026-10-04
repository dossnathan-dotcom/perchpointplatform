ALTER TABLE identity_invitations
  ADD COLUMN relationship_type text,
  ADD COLUMN relationship_id uuid,
  ADD COLUMN scope_payload jsonb NOT NULL DEFAULT '{}'::jsonb,
  ADD COLUMN approval_status text NOT NULL DEFAULT 'approved'
    CHECK (approval_status IN ('pending', 'approved', 'denied')),
  ADD COLUMN accepted_identity_id uuid,
  ADD COLUMN replaced_by uuid;

ALTER TABLE access_requests
  ADD COLUMN purpose text NOT NULL DEFAULT 'access request',
  ADD COLUMN scope_type text NOT NULL DEFAULT 'organization',
  ADD COLUMN scope_resource_id uuid,
  ADD COLUMN requested_until timestamptz,
  ADD COLUMN decided_at timestamptz;

ALTER TABLE service_principals
  ADD COLUMN audience text NOT NULL DEFAULT 'perchpoint-worker',
  ADD COLUMN capabilities text[] NOT NULL DEFAULT ARRAY[]::text[],
  ADD COLUMN last_used_at timestamptz,
  ADD COLUMN revoked_at timestamptz;

ALTER TABLE identity_sessions
  ADD COLUMN refresh_family_id uuid,
  ADD COLUMN refresh_generation integer NOT NULL DEFAULT 0,
  ADD COLUMN refresh_reuse_detected_at timestamptz;

ALTER TABLE security_events
  ADD COLUMN request_id uuid,
  ADD COLUMN actor_account_id uuid,
  ADD COLUMN resource_type text,
  ADD COLUMN resource_id uuid,
  ADD COLUMN reason_code text,
  ADD COLUMN details jsonb NOT NULL DEFAULT '{}'::jsonb;

CREATE TABLE identity_contact_history (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  identity_id uuid NOT NULL REFERENCES identity_accounts(id),
  contact_kind text NOT NULL CHECK (contact_kind IN ('email', 'phone')),
  previous_value text,
  proposed_value text NOT NULL,
  status text NOT NULL CHECK (status IN ('pending', 'verified', 'cancelled')),
  requested_at timestamptz NOT NULL DEFAULT now(),
  verified_at timestamptz,
  cooldown_until timestamptz,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE delegation_events (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  delegation_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  action text NOT NULL CHECK (action IN ('created', 'used', 'revoked', 'expired')),
  request_id uuid,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE membership_role_assignments (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  membership_id uuid NOT NULL REFERENCES memberships(id),
  bundle_id uuid NOT NULL REFERENCES role_bundles(id),
  assigned_by uuid,
  effective_at timestamptz NOT NULL DEFAULT now(),
  ended_at timestamptz,
  policy_version text NOT NULL DEFAULT 'phase6-1',
  PRIMARY KEY (organization_id, id),
  CHECK (ended_at IS NULL OR ended_at > effective_at)
);

ALTER TABLE identity_contact_history ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_contact_history FORCE ROW LEVEL SECURITY;
ALTER TABLE delegation_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE delegation_events FORCE ROW LEVEL SECURITY;
ALTER TABLE membership_role_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE membership_role_assignments FORCE ROW LEVEL SECURITY;

CREATE POLICY identity_contact_org ON identity_contact_history
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));
CREATE POLICY delegation_event_org ON delegation_events
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));
CREATE POLICY membership_role_org ON membership_role_assignments
  USING (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.actor_in_org(perchpoint.current_org()));

REVOKE UPDATE, DELETE ON delegation_events FROM perchpoint_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON identity_contact_history, membership_role_assignments
  TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON delegation_events TO perchpoint_runtime;
GRANT SELECT, INSERT, UPDATE, DELETE ON delegation_events TO perchpoint_definer;

GRANT INSERT, UPDATE ON capabilities, role_bundles TO perchpoint_definer;
SET LOCAL ROLE perchpoint_definer;

INSERT INTO capabilities (code, family, description) VALUES
  ('identity.profile.read', 'identity', 'Read own identity profile'),
  ('session.read', 'identity', 'Read own sessions'),
  ('session.revoke', 'identity', 'Revoke own sessions'),
  ('invitation.create', 'identity', 'Create governed invitations'),
  ('membership.read', 'identity', 'Read memberships'),
  ('membership.grant', 'identity', 'Grant approved memberships'),
  ('role.manage', 'identity', 'Manage role assignments'),
  ('scope.manage', 'identity', 'Manage scope assignments'),
  ('access.request', 'identity', 'Request access'),
  ('access.approve', 'identity', 'Decide routed access requests'),
  ('delegation.grant', 'authorization', 'Grant bounded authority'),
  ('delegation.revoke', 'authorization', 'Revoke bounded authority'),
  ('property.read', 'property', 'Read authorized property records'),
  ('property.manage', 'property', 'Manage authorized property records'),
  ('resident.read', 'leasing', 'Read authorized resident records'),
  ('household.read', 'leasing', 'Read authorized household records'),
  ('inquiry.manage', 'leasing', 'Manage authorized inquiries'),
  ('leasing.coordinate', 'leasing', 'Coordinate leasing work'),
  ('maintenance.coordinate', 'maintenance', 'Coordinate maintenance'),
  ('work.assign', 'maintenance', 'Manage assigned work'),
  ('document.read', 'documents', 'Read authorized documents'),
  ('document.manage', 'documents', 'Manage authorized documents'),
  ('search.read', 'search', 'Search authorized records'),
  ('export.create', 'exports', 'Generate an authorized export'),
  ('expense.approve', 'finance', 'Approve an authorized expense'),
  ('approval.owner', 'finance', 'Exercise owner-reserved approval'),
  ('accounting.read', 'finance', 'Read operational accounting'),
  ('vendor.admin', 'vendor', 'Administer vendor workers'),
  ('service.manage', 'platform', 'Manage service principals'),
  ('security.read', 'platform', 'Read security administration records'),
  ('audit.read', 'platform', 'Read immutable audit history'),
  ('platform.configure', 'platform', 'Configure technical platform policy')
ON CONFLICT (code) DO UPDATE SET family = EXCLUDED.family, description = EXCLUDED.description;

INSERT INTO role_bundles (id, name, version)
SELECT gen_random_uuid(), name, 1
FROM (VALUES
  ('owner'), ('platform_admin'), ('project_manager'), ('leasing_staff'),
  ('maintenance_coordinator'), ('accounting'), ('limited_approver'), ('applicant'),
  ('resident'), ('household_adult'), ('guarantor'), ('vendor_admin'),
  ('vendor_worker'), ('technician'), ('cleaner'), ('service_principal')
) AS roles(name)
ON CONFLICT (name) DO NOTHING;

RESET ROLE;

CREATE OR REPLACE FUNCTION perchpoint.recovery_code_material(account uuid)
RETURNS TABLE (code_id uuid, code_hash text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT code.id, code.code_hash
  FROM identity_recovery_codes code
  JOIN identity_accounts identity ON identity.id = code.identity_id
  WHERE identity.account_id = account AND code.used_at IS NULL
  ORDER BY code.created_at
$$;

CREATE OR REPLACE FUNCTION perchpoint.consume_recovery_code(account uuid, code_id uuid)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE updated integer;
BEGIN
  UPDATE identity_recovery_codes code
  SET used_at = now()
  WHERE code.id = code_id AND code.used_at IS NULL
    AND code.identity_id IN (SELECT id FROM identity_accounts WHERE account_id = account);
  GET DIAGNOSTICS updated = ROW_COUNT;
  RETURN updated = 1;
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.recovery_code_material(uuid) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.consume_recovery_code(uuid, uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.recovery_code_material(uuid), perchpoint.consume_recovery_code(uuid, uuid)
  TO perchpoint_runtime;

CREATE INDEX identity_sessions_active_account_idx
  ON identity_sessions (identity_id, absolute_expires_at) WHERE revoked_at IS NULL;
CREATE INDEX identity_invitations_active_email_idx
  ON identity_invitations (lower(email), expires_at) WHERE accepted_at IS NULL AND revoked_at IS NULL;
CREATE INDEX delegation_events_delegation_idx
  ON delegation_events (organization_id, delegation_id, occurred_at);

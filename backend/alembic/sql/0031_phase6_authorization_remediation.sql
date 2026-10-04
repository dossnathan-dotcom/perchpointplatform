-- Phase 6 independent-review authorization remediation.

ALTER TABLE authorization_scopes
  ADD COLUMN IF NOT EXISTS scope_value text;

ALTER TABLE service_credentials
  ADD COLUMN IF NOT EXISTS last_used_at timestamptz,
  ADD COLUMN IF NOT EXISTS bound_worker_name text;

ALTER TABLE worker_assignments
  ADD COLUMN IF NOT EXISTS work_order_id uuid;

ALTER TABLE access_review_campaigns
  ADD COLUMN IF NOT EXISTS trigger_kind text NOT NULL DEFAULT 'quarterly'
    CHECK (trigger_kind IN ('quarterly', 'material_change')),
  ADD COLUMN IF NOT EXISTS policy_version text NOT NULL DEFAULT 'phase6-2';

CREATE TABLE access_grants (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  account_id uuid NOT NULL REFERENCES accounts(id),
  membership_id uuid NOT NULL REFERENCES memberships(id),
  capability text NOT NULL REFERENCES capabilities(code),
  scope_type text NOT NULL,
  scope_resource_id uuid,
  purpose text NOT NULL,
  justification text NOT NULL,
  starts_at timestamptz NOT NULL DEFAULT now(),
  ends_at timestamptz NOT NULL,
  approved_by uuid NOT NULL REFERENCES accounts(id),
  access_request_id uuid NOT NULL,
  revoked_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, access_request_id),
  CHECK (approved_by <> account_id),
  CHECK (ends_at > starts_at)
);

CREATE TABLE authority_change_approvals (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  membership_id uuid NOT NULL REFERENCES memberships(id),
  target_account_id uuid NOT NULL REFERENCES accounts(id),
  action text NOT NULL CHECK (action IN ('role', 'scope')),
  role_name text,
  scope_type text,
  resource_id uuid,
  reason text NOT NULL,
  approved_by uuid NOT NULL REFERENCES accounts(id),
  approved_at timestamptz NOT NULL DEFAULT now(),
  expires_at timestamptz NOT NULL,
  consumed_at timestamptz,
  consumed_by uuid REFERENCES accounts(id),
  PRIMARY KEY (organization_id, id),
  CHECK (approved_by <> target_account_id),
  CHECK (
    (action = 'role' AND role_name IS NOT NULL AND scope_type IS NULL)
    OR (action = 'scope' AND scope_type IS NOT NULL AND role_name IS NULL)
  )
);

CREATE TABLE privileged_recovery_events (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  recovery_id uuid NOT NULL,
  event_type text NOT NULL CHECK (event_type IN ('opened', 'approved', 'completed', 'metadata_changed')),
  actor_id uuid,
  from_status text,
  to_status text NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, recovery_id)
    REFERENCES privileged_recoveries(organization_id, id)
);

INSERT INTO privileged_recovery_events (
  organization_id, recovery_id, event_type, actor_id, to_status, occurred_at
)
SELECT organization_id, id, 'opened', initiator_account, status, created_at
FROM privileged_recoveries;

CREATE OR REPLACE FUNCTION perchpoint.record_privileged_recovery_event()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    RAISE EXCEPTION 'privileged_recovery_append_only';
  END IF;
  IF TG_OP = 'UPDATE' AND (
    NEW.organization_id <> OLD.organization_id
    OR NEW.id <> OLD.id
    OR NEW.subject_account <> OLD.subject_account
    OR NEW.initiator_account <> OLD.initiator_account
    OR NEW.approver_account IS DISTINCT FROM OLD.approver_account
    OR NEW.evidence_note <> OLD.evidence_note
  ) THEN
    RAISE EXCEPTION 'privileged_recovery_identity_immutable';
  END IF;
  INSERT INTO privileged_recovery_events (
    organization_id, recovery_id, event_type, actor_id, from_status, to_status
  ) VALUES (
    NEW.organization_id,
    NEW.id,
    CASE
      WHEN TG_OP = 'INSERT' THEN 'opened'
      WHEN NEW.status = 'ready' AND OLD.status = 'waiting' THEN 'approved'
      WHEN NEW.status = 'completed' AND OLD.status = 'ready' THEN 'completed'
      ELSE 'metadata_changed'
    END,
    perchpoint.current_actor(),
    CASE WHEN TG_OP = 'INSERT' THEN NULL ELSE OLD.status END,
    NEW.status
  );
  RETURN NEW;
END
$$;

CREATE TRIGGER privileged_recovery_history
AFTER INSERT OR UPDATE OR DELETE ON privileged_recoveries
FOR EACH ROW EXECUTE FUNCTION perchpoint.record_privileged_recovery_event();

CREATE TABLE authorized_business_actions (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  actor_id uuid NOT NULL,
  action_type text NOT NULL,
  capability text NOT NULL REFERENCES capabilities(code),
  resource_type text NOT NULL,
  resource_id uuid,
  amount_minor integer CHECK (amount_minor IS NULL OR amount_minor >= 0),
  decision_type text NOT NULL,
  related_transaction_key text,
  idempotency_key text NOT NULL,
  request_id uuid NOT NULL,
  delegation_id uuid,
  status text NOT NULL DEFAULT 'authorized' CHECK (status IN ('authorized', 'denied', 'executed', 'cancelled')),
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, actor_id, idempotency_key),
  FOREIGN KEY (organization_id, delegation_id) REFERENCES delegations(organization_id, id)
);

ALTER TABLE delegation_usage
  ADD COLUMN IF NOT EXISTS business_action_id uuid;

CREATE TABLE access_review_remediations (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  review_item_id uuid NOT NULL,
  action text NOT NULL,
  status text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'completed', 'failed')),
  due_at timestamptz NOT NULL,
  completed_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE property_authority_limits (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  property_id uuid NOT NULL,
  monthly_budget_minor integer NOT NULL CHECK (monthly_budget_minor >= 0),
  monthly_rent_minor integer NOT NULL CHECK (monthly_rent_minor >= 0),
  currency text NOT NULL DEFAULT 'USD',
  effective_at timestamptz NOT NULL DEFAULT now(),
  effective_until timestamptz,
  source_kind text NOT NULL,
  source_reference text NOT NULL,
  approved_by uuid,
  PRIMARY KEY (organization_id, property_id),
  FOREIGN KEY (organization_id, property_id) REFERENCES properties(organization_id, id)
);

CREATE TABLE business_action_catalog (
  decision_type text PRIMARY KEY,
  action_type text NOT NULL,
  resource_type text NOT NULL,
  financial boolean NOT NULL,
  capital boolean NOT NULL,
  owner_reserved boolean NOT NULL,
  policy_version text NOT NULL
);

INSERT INTO business_action_catalog (
  decision_type, action_type, resource_type, financial, capital, owner_reserved, policy_version
) VALUES
  ('routine_purchase', 'purchase_authorization', 'property', true, false, false, 'phase6-2'),
  ('emergency_stabilization', 'purchase_authorization', 'property', true, false, false, 'phase6-2'),
  ('unavoidable_imminent_harm', 'purchase_authorization', 'property', true, false, false, 'phase6-2'),
  ('capital_project', 'purchase_authorization', 'property', true, true, true, 'phase6-2');

CREATE OR REPLACE FUNCTION perchpoint.validate_delegation_bounds()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
BEGIN
  IF NEW.approved_by IS NULL
     OR NEW.approved_by IN (NEW.grantor_id, NEW.grantee_id)
     OR NOT EXISTS (
       SELECT 1 FROM memberships approval_membership
       WHERE approval_membership.organization_id = NEW.organization_id
         AND approval_membership.account_id = NEW.approved_by
         AND approval_membership.role_name = 'owner'
         AND approval_membership.effective_at <= now()
         AND (
           approval_membership.ended_at IS NULL
           OR approval_membership.ended_at > now()
         )
     ) THEN
    RAISE EXCEPTION 'delegation_independent_owner_approval_required';
  END IF;
  IF NEW.resource_id IS NULL
     OR (NEW.resource_type = 'organization' AND NEW.resource_id <> NEW.organization_id)
     OR cardinality(NEW.decision_types) = 0 THEN
    RAISE EXCEPTION 'delegation_bounds_required';
  END IF;
  IF NEW.capability = 'expense.approve' AND (
    NEW.resource_type <> 'property'
    OR NEW.amount_ceiling_minor IS NULL
    OR NEW.amount_ceiling_minor > 120000
    OR EXISTS (
      SELECT 1
      FROM unnest(NEW.decision_types) requested(decision_type)
      LEFT JOIN business_action_catalog catalog
        ON catalog.decision_type = requested.decision_type
      WHERE catalog.decision_type IS NULL
         OR NOT catalog.financial
         OR catalog.capital
         OR catalog.owner_reserved
    )
  ) THEN
    RAISE EXCEPTION 'delegation_financial_bounds_invalid';
  END IF;
  RETURN NEW;
END
$$;

CREATE TRIGGER delegation_bounds_guard
BEFORE INSERT OR UPDATE OF capability, amount_ceiling_minor, resource_type, resource_id,
  decision_types, approved_by ON delegations
FOR EACH ROW EXECUTE FUNCTION perchpoint.validate_delegation_bounds();

ALTER TABLE access_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_grants FORCE ROW LEVEL SECURITY;
ALTER TABLE authority_change_approvals ENABLE ROW LEVEL SECURITY;
ALTER TABLE authority_change_approvals FORCE ROW LEVEL SECURITY;
ALTER TABLE authorized_business_actions ENABLE ROW LEVEL SECURITY;
ALTER TABLE authorized_business_actions FORCE ROW LEVEL SECURITY;
ALTER TABLE access_review_remediations ENABLE ROW LEVEL SECURITY;
ALTER TABLE access_review_remediations FORCE ROW LEVEL SECURITY;
ALTER TABLE property_authority_limits ENABLE ROW LEVEL SECURITY;
ALTER TABLE property_authority_limits FORCE ROW LEVEL SECURITY;
ALTER TABLE privileged_recovery_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE privileged_recovery_events FORCE ROW LEVEL SECURITY;

GRANT SELECT, INSERT, UPDATE ON access_grants, authority_change_approvals, authorized_business_actions,
  access_review_remediations, property_authority_limits TO perchpoint_runtime, perchpoint_definer;
REVOKE DELETE ON access_grants, authority_change_approvals, authorized_business_actions,
  access_review_remediations, property_authority_limits FROM perchpoint_runtime;
GRANT SELECT ON privileged_recovery_events TO perchpoint_runtime, perchpoint_definer;
GRANT INSERT ON privileged_recovery_events TO perchpoint_definer;
REVOKE INSERT, UPDATE, DELETE ON privileged_recovery_events FROM perchpoint_runtime;
REVOKE UPDATE, DELETE ON privileged_recovery_events FROM perchpoint_definer;
GRANT INSERT, UPDATE, DELETE ON role_bundle_capabilities TO perchpoint_definer;
GRANT SELECT ON memberships, authorization_scopes, membership_scope_assignments,
  properties, spaces, listings, business_action_catalog
  TO perchpoint_definer;
GRANT SELECT ON business_action_catalog TO perchpoint_runtime;
GRANT INSERT ON authorization_scopes, membership_scope_assignments
  TO perchpoint_definer;

SET LOCAL ROLE perchpoint_definer;

INSERT INTO capabilities (code, family, description) VALUES
  ('party.create', 'leasing', 'Create an authorized party record'),
  ('maintenance.case.read', 'maintenance', 'Read an assigned maintenance case'),
  ('maintenance.case.write', 'maintenance', 'Write an assigned maintenance case'),
  ('purchase.authorize', 'finance', 'Persist a bounded purchase authorization'),
  ('import.manage', 'data', 'Stage and reconcile governed data imports')
ON CONFLICT (code) DO UPDATE
SET family = EXCLUDED.family, description = EXCLUDED.description;

INSERT INTO role_bundles (id, name, version)
SELECT gen_random_uuid(), role_name, 2
FROM (VALUES
  ('owner'), ('platform_admin'), ('project_manager'), ('operations_manager'),
  ('leasing'), ('leasing_staff'), ('maintenance'), ('maintenance_coordinator'),
  ('accounting'), ('limited_approver'), ('applicant'), ('resident'),
  ('household_adult'), ('guarantor'), ('vendor_admin'), ('vendor_worker'),
  ('technician'), ('cleaner'), ('service_principal')
) AS roles(role_name)
ON CONFLICT (name) DO UPDATE SET version = GREATEST(role_bundles.version, 2);

DELETE FROM role_bundle_capabilities AS assignment
USING role_bundles AS bundle
WHERE assignment.bundle_id = bundle.id
  AND bundle.name = 'owner'
  AND assignment.capability = 'role.manage';

WITH grants(role_name, capability) AS (
  VALUES
    ('owner','identity.profile.read'), ('owner','session.read'), ('owner','session.revoke'),
    ('owner','invitation.create'), ('owner','membership.read'), ('owner','access.request'),
    ('owner','access.approve'), ('owner','delegation.grant'), ('owner','delegation.revoke'),
    ('owner','property.read'), ('owner','property.manage'), ('owner','resident.read'),
    ('owner','party.create'), ('owner','household.read'), ('owner','inquiry.manage'),
    ('owner','maintenance.coordinate'), ('owner','maintenance.case.read'),
    ('owner','maintenance.case.write'), ('owner','work.assign'), ('owner','document.read'),
    ('owner','document.manage'), ('owner','search.read'), ('owner','export.create'),
    ('owner','expense.approve'), ('owner','purchase.authorize'), ('owner','import.manage'),
    ('owner','approval.owner'),
    ('owner','accounting.read'), ('owner','vendor.admin'), ('owner','vendor.worker.approve'),
    ('owner','security.read'), ('owner','audit.read'),
    ('project_manager','identity.profile.read'), ('project_manager','session.read'),
    ('project_manager','session.revoke'), ('project_manager','invitation.create'),
    ('project_manager','membership.read'), ('project_manager','access.request'),
    ('project_manager','access.approve'), ('project_manager','delegation.grant'),
    ('project_manager','delegation.revoke'), ('project_manager','property.read'),
    ('project_manager','property.manage'), ('project_manager','resident.read'),
    ('project_manager','party.create'), ('project_manager','household.read'),
    ('project_manager','inquiry.manage'), ('project_manager','maintenance.coordinate'),
    ('project_manager','maintenance.case.read'), ('project_manager','maintenance.case.write'),
    ('project_manager','work.assign'), ('project_manager','document.read'),
    ('project_manager','document.manage'), ('project_manager','search.read'),
    ('project_manager','export.create'), ('project_manager','expense.approve'),
    ('project_manager','purchase.authorize'), ('project_manager','import.manage'),
    ('project_manager','vendor.admin'),
    ('project_manager','vendor.worker.approve'), ('project_manager','security.read'),
    ('project_manager','audit.read'),
    ('operations_manager','identity.profile.read'), ('operations_manager','session.read'),
    ('operations_manager','session.revoke'), ('operations_manager','invitation.create'),
    ('operations_manager','membership.read'), ('operations_manager','access.request'),
    ('operations_manager','access.approve'), ('operations_manager','delegation.grant'),
    ('operations_manager','delegation.revoke'), ('operations_manager','property.read'),
    ('operations_manager','property.manage'), ('operations_manager','resident.read'),
    ('operations_manager','party.create'), ('operations_manager','household.read'),
    ('operations_manager','inquiry.manage'), ('operations_manager','maintenance.coordinate'),
    ('operations_manager','maintenance.case.read'), ('operations_manager','maintenance.case.write'),
    ('operations_manager','work.assign'), ('operations_manager','document.read'),
    ('operations_manager','document.manage'), ('operations_manager','search.read'),
    ('operations_manager','export.create'), ('operations_manager','expense.approve'),
    ('operations_manager','purchase.authorize'), ('operations_manager','import.manage'),
    ('operations_manager','vendor.admin'),
    ('operations_manager','vendor.worker.approve'), ('operations_manager','security.read'),
    ('operations_manager','audit.read'),
    ('leasing','identity.profile.read'), ('leasing','session.read'), ('leasing','session.revoke'),
    ('leasing','invitation.create'), ('leasing','access.request'), ('leasing','property.read'),
    ('leasing','property.manage'), ('leasing','resident.read'), ('leasing','party.create'),
    ('leasing','household.read'), ('leasing','inquiry.manage'), ('leasing','document.read'),
    ('leasing','document.manage'), ('leasing','search.read'), ('leasing','expense.approve'),
    ('leasing','audit.read'),
    ('leasing_staff','identity.profile.read'), ('leasing_staff','session.read'),
    ('leasing_staff','session.revoke'), ('leasing_staff','invitation.create'),
    ('leasing_staff','access.request'), ('leasing_staff','property.read'),
    ('leasing_staff','property.manage'), ('leasing_staff','resident.read'),
    ('leasing_staff','party.create'), ('leasing_staff','household.read'),
    ('leasing_staff','inquiry.manage'), ('leasing_staff','document.read'),
    ('leasing_staff','document.manage'), ('leasing_staff','search.read'),
    ('maintenance','identity.profile.read'), ('maintenance','session.read'),
    ('maintenance','property.read'), ('maintenance','maintenance.coordinate'),
    ('maintenance','maintenance.case.read'), ('maintenance','maintenance.case.write'),
    ('maintenance','work.assign'), ('maintenance','document.read'),
    ('maintenance_coordinator','identity.profile.read'), ('maintenance_coordinator','session.read'),
    ('maintenance_coordinator','session.revoke'), ('maintenance_coordinator','invitation.create'),
    ('maintenance_coordinator','access.request'), ('maintenance_coordinator','property.read'),
    ('maintenance_coordinator','property.manage'), ('maintenance_coordinator','resident.read'),
    ('maintenance_coordinator','party.create'), ('maintenance_coordinator','household.read'),
    ('maintenance_coordinator','maintenance.coordinate'), ('maintenance_coordinator','maintenance.case.read'),
    ('maintenance_coordinator','maintenance.case.write'), ('maintenance_coordinator','work.assign'),
    ('maintenance_coordinator','document.read'), ('maintenance_coordinator','document.manage'),
    ('maintenance_coordinator','search.read'), ('maintenance_coordinator','expense.approve'),
    ('maintenance_coordinator','purchase.authorize'), ('maintenance_coordinator','vendor.admin'),
    ('maintenance_coordinator','vendor.worker.approve'),
    ('platform_admin','identity.profile.read'), ('platform_admin','session.read'),
    ('platform_admin','session.revoke'), ('platform_admin','membership.read'),
    ('platform_admin','membership.grant'), ('platform_admin','role.manage'),
    ('platform_admin','scope.manage'), ('platform_admin','platform.configure'),
    ('platform_admin','security.read'), ('platform_admin','service.manage'),
    ('platform_admin','audit.read'), ('platform_admin','invitation.create'),
    ('platform_admin','search.read'),
    ('accounting','identity.profile.read'), ('accounting','session.read'),
    ('accounting','accounting.read'), ('accounting','export.create'),
    ('accounting','document.read'), ('accounting','search.read'),
    ('limited_approver','identity.profile.read'), ('limited_approver','session.read'),
    ('limited_approver','expense.approve'), ('limited_approver','purchase.authorize'),
    ('applicant','identity.profile.read'), ('applicant','session.read'), ('applicant','access.request'),
    ('applicant','session.revoke'), ('applicant','resident.read'),
    ('applicant','household.read'), ('applicant','document.read'),
    ('resident','identity.profile.read'), ('resident','session.read'), ('resident','access.request'),
    ('resident','session.revoke'), ('resident','resident.read'),
    ('resident','household.read'), ('resident','document.read'),
    ('household_adult','identity.profile.read'), ('household_adult','session.read'), ('household_adult','access.request'),
    ('household_adult','session.revoke'), ('household_adult','resident.read'),
    ('household_adult','household.read'), ('household_adult','document.read'),
    ('guarantor','identity.profile.read'), ('guarantor','session.read'), ('guarantor','document.read'),
    ('guarantor','access.request'),
    ('vendor_admin','identity.profile.read'), ('vendor_admin','session.read'), ('vendor_admin','access.request'),
    ('vendor_admin','vendor.admin'), ('vendor_admin','work.assign'),
    ('vendor_admin','maintenance.case.read'), ('vendor_admin','search.read'),
    ('vendor_worker','identity.profile.read'), ('vendor_worker','session.read'), ('vendor_worker','access.request'),
    ('vendor_worker','work.assign'), ('vendor_worker','maintenance.case.read'),
    ('vendor_worker','maintenance.case.write'), ('vendor_worker','search.read'),
    ('technician','identity.profile.read'), ('technician','session.read'), ('technician','access.request'),
    ('technician','work.assign'), ('technician','maintenance.case.read'),
    ('technician','maintenance.case.write'), ('technician','search.read'),
    ('cleaner','identity.profile.read'), ('cleaner','session.read'), ('cleaner','access.request'),
    ('cleaner','work.assign'), ('cleaner','maintenance.case.read'),
    ('cleaner','maintenance.case.write'), ('cleaner','search.read')
)
INSERT INTO role_bundle_capabilities (bundle_id, capability)
SELECT bundle.id, grants.capability
FROM grants JOIN role_bundles bundle ON bundle.name = grants.role_name
ON CONFLICT DO NOTHING;

RESET ROLE;

-- Existing accepted memberships receive an explicit organization scope. New
-- memberships receive no authority until an approved scope is assigned.
SET LOCAL ROLE perchpoint_definer;
INSERT INTO authorization_scopes (organization_id, id, scope_type, resource_id)
SELECT membership.organization_id, gen_random_uuid(), 'organization', membership.organization_id
FROM memberships membership
WHERE NOT EXISTS (
  SELECT 1
  FROM membership_scope_assignments assignment
  JOIN authorization_scopes scope
    ON scope.organization_id = assignment.organization_id AND scope.id = assignment.scope_id
  WHERE assignment.membership_id = membership.id
    AND assignment.effective_at <= now()
    AND (assignment.ended_at IS NULL OR assignment.ended_at > now())
)
GROUP BY membership.organization_id
ON CONFLICT DO NOTHING;

INSERT INTO membership_scope_assignments (organization_id, id, membership_id, scope_id)
SELECT membership.organization_id, gen_random_uuid(), membership.id, scope.id
FROM memberships membership
JOIN authorization_scopes scope
  ON scope.organization_id = membership.organization_id
 AND scope.scope_type = 'organization'
 AND scope.resource_id = membership.organization_id
WHERE membership.role_name IN (
  'owner', 'platform_admin', 'project_manager', 'operations_manager',
  'leasing', 'leasing_staff', 'maintenance', 'maintenance_coordinator',
  'accounting', 'limited_approver'
)
AND NOT EXISTS (
  SELECT 1 FROM membership_scope_assignments existing
  WHERE existing.membership_id = membership.id
);
RESET ROLE;

SET LOCAL ROLE perchpoint_definer;
INSERT INTO property_authority_limits (
  organization_id, property_id, monthly_budget_minor, monthly_rent_minor,
  source_kind, source_reference
)
SELECT property.organization_id, property.id, 120000, 150000,
       'synthetic_fixture', 'phase6-approved-customization-Q114-Q118'
FROM properties property
ON CONFLICT (organization_id, property_id) DO NOTHING;
RESET ROLE;

CREATE OR REPLACE FUNCTION perchpoint.current_membership(account uuid)
RETURNS TABLE (organization_id uuid, role_name text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT membership.organization_id, membership.role_name
  FROM memberships membership
  WHERE membership.id = NULLIF(current_setting('app.membership_id', true), '')::uuid
    AND membership.account_id = account
    AND membership.organization_id = perchpoint.current_org()
    AND membership.effective_at <= now()
    AND (membership.ended_at IS NULL OR membership.ended_at > now())
$$;

CREATE OR REPLACE FUNCTION perchpoint.list_memberships(account uuid)
RETURNS TABLE (membership_id uuid, organization_id uuid, role_name text)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT membership.id, membership.organization_id, membership.role_name
  FROM memberships membership
  WHERE account = perchpoint.current_actor()
    AND membership.account_id = perchpoint.current_actor()
    AND membership.effective_at <= now()
    AND (membership.ended_at IS NULL OR membership.ended_at > now())
  ORDER BY membership.effective_at DESC, membership.id
$$;

DROP FUNCTION perchpoint.access_directory();
CREATE FUNCTION perchpoint.access_directory()
RETURNS TABLE (
  account_id uuid,
  email text,
  membership_id uuid,
  role_name text,
  lifecycle_status text
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT account.id, account.email, membership.id, membership.role_name,
         COALESCE(identity.status, 'active')
  FROM memberships membership
  JOIN accounts account ON account.id = membership.account_id
  LEFT JOIN identity_accounts identity ON identity.account_id = account.id
  WHERE membership.organization_id = perchpoint.current_org()
    AND membership.effective_at <= now()
    AND (membership.ended_at IS NULL OR membership.ended_at > now())
    AND perchpoint.current_role() IN (
      'owner', 'platform_admin', 'project_manager', 'operations_manager'
    )
  ORDER BY account.email
$$;

CREATE FUNCTION perchpoint.role_for_account(account uuid)
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT membership.role_name
  FROM memberships membership
  WHERE membership.account_id = account
    AND membership.organization_id = perchpoint.current_org()
    AND membership.effective_at <= now()
    AND (membership.ended_at IS NULL OR membership.ended_at > now())
  ORDER BY membership.effective_at DESC, membership.id
  LIMIT 1
$$;

CREATE OR REPLACE FUNCTION perchpoint.current_role()
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT membership.role_name
  FROM memberships membership
  WHERE membership.id = NULLIF(current_setting('app.membership_id', true), '')::uuid
    AND membership.account_id = perchpoint.current_actor()
    AND membership.organization_id = perchpoint.current_org()
    AND membership.effective_at <= now()
    AND (membership.ended_at IS NULL OR membership.ended_at > now())
$$;

CREATE OR REPLACE FUNCTION perchpoint.actor_in_org(target uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1
    FROM memberships membership
    WHERE membership.id = NULLIF(current_setting('app.membership_id', true), '')::uuid
      AND membership.account_id = perchpoint.current_actor()
      AND membership.organization_id = target
      AND membership.effective_at <= now()
      AND (membership.ended_at IS NULL OR membership.ended_at > now())
  ) OR EXISTS (
    SELECT 1 FROM service_principals principal
    WHERE principal.id = perchpoint.current_actor()
      AND principal.organization_id = target
      AND principal.status = 'active'
      AND principal.revoked_at IS NULL
      AND (principal.expires_at IS NULL OR principal.expires_at > now())
  )
$$;

CREATE FUNCTION perchpoint.resolve_authority_context(
  account uuid, target_org uuid, requested_membership uuid
)
RETURNS TABLE (identity_id uuid, membership_id uuid)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT identity.id, membership.id
  FROM memberships membership
  LEFT JOIN identity_accounts identity ON identity.account_id = membership.account_id
  WHERE membership.account_id = account
    AND membership.organization_id = target_org
    AND (requested_membership IS NULL OR membership.id = requested_membership)
    AND membership.effective_at <= now()
    AND (membership.ended_at IS NULL OR membership.ended_at > now())
  ORDER BY membership.effective_at DESC
  LIMIT 1
$$;

CREATE FUNCTION perchpoint.has_capability(required text)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1
    FROM memberships membership
    JOIN role_bundles bundle ON bundle.name = membership.role_name
    JOIN role_bundle_capabilities capability ON capability.bundle_id = bundle.id
    WHERE membership.id = NULLIF(current_setting('app.membership_id', true), '')::uuid
      AND membership.account_id = perchpoint.current_actor()
      AND membership.organization_id = perchpoint.current_org()
      AND membership.effective_at <= now()
      AND (membership.ended_at IS NULL OR membership.ended_at > now())
      AND capability.capability = required
  ) OR EXISTS (
    SELECT 1 FROM access_grants grant_record
    WHERE grant_record.membership_id = NULLIF(current_setting('app.membership_id', true), '')::uuid
      AND grant_record.account_id = perchpoint.current_actor()
      AND grant_record.organization_id = perchpoint.current_org()
      AND grant_record.capability = required
      AND grant_record.starts_at <= now()
      AND grant_record.ends_at > now()
      AND grant_record.revoked_at IS NULL
  ) OR EXISTS (
    SELECT 1 FROM service_principals principal
    WHERE principal.id = perchpoint.current_actor()
      AND principal.organization_id = perchpoint.current_org()
      AND principal.status = 'active'
      AND principal.revoked_at IS NULL
      AND (principal.expires_at IS NULL OR principal.expires_at > now())
      AND required = ANY(principal.capabilities)
  )
$$;

CREATE FUNCTION perchpoint.scope_allows(kind text, resource uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1
    FROM membership_scope_assignments assignment
    JOIN authorization_scopes scope
      ON scope.organization_id = assignment.organization_id AND scope.id = assignment.scope_id
    WHERE assignment.membership_id = NULLIF(current_setting('app.membership_id', true), '')::uuid
      AND assignment.organization_id = perchpoint.current_org()
      AND assignment.effective_at <= now()
      AND (assignment.ended_at IS NULL OR assignment.ended_at > now())
      AND (
        (scope.scope_type = 'organization' AND scope.resource_id = perchpoint.current_org())
        OR (scope.scope_type = kind AND (scope.resource_id IS NULL OR scope.resource_id = resource))
      )
  ) OR EXISTS (
    SELECT 1 FROM access_grants grant_record
    WHERE grant_record.membership_id = NULLIF(current_setting('app.membership_id', true), '')::uuid
      AND grant_record.organization_id = perchpoint.current_org()
      AND grant_record.starts_at <= now() AND grant_record.ends_at > now()
      AND grant_record.revoked_at IS NULL
      AND (
        grant_record.scope_type = 'organization'
        OR (grant_record.scope_type = kind
            AND (grant_record.scope_resource_id IS NULL OR grant_record.scope_resource_id = resource))
      )
  )
$$;

CREATE FUNCTION perchpoint.authorized_for(required text, kind text, resource uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1
    FROM memberships membership
    JOIN role_bundles bundle ON bundle.name = membership.role_name
    JOIN role_bundle_capabilities capability ON capability.bundle_id = bundle.id
    JOIN membership_scope_assignments assignment
      ON assignment.organization_id = membership.organization_id
     AND assignment.membership_id = membership.id
    JOIN authorization_scopes scope
      ON scope.organization_id = assignment.organization_id
     AND scope.id = assignment.scope_id
    WHERE membership.id = NULLIF(current_setting('app.membership_id', true), '')::uuid
      AND membership.account_id = perchpoint.current_actor()
      AND membership.organization_id = perchpoint.current_org()
      AND membership.effective_at <= now()
      AND (membership.ended_at IS NULL OR membership.ended_at > now())
      AND assignment.effective_at <= now()
      AND (assignment.ended_at IS NULL OR assignment.ended_at > now())
      AND capability.capability = required
      AND (
        (scope.scope_type = 'organization' AND scope.resource_id = perchpoint.current_org())
        OR (scope.scope_type = kind AND (scope.resource_id IS NULL OR scope.resource_id = resource))
      )
  ) OR EXISTS (
    SELECT 1
    FROM access_grants grant_record
    WHERE grant_record.membership_id = NULLIF(current_setting('app.membership_id', true), '')::uuid
      AND grant_record.account_id = perchpoint.current_actor()
      AND grant_record.organization_id = perchpoint.current_org()
      AND grant_record.capability = required
      AND grant_record.starts_at <= now()
      AND grant_record.ends_at > now()
      AND grant_record.revoked_at IS NULL
      AND (
        grant_record.scope_type = 'organization'
        OR (
          grant_record.scope_type = kind
          AND (
            grant_record.scope_resource_id IS NULL
            OR grant_record.scope_resource_id = resource
          )
        )
      )
  ) OR EXISTS (
    SELECT 1
    FROM service_principals principal
    WHERE principal.id = perchpoint.current_actor()
      AND principal.organization_id = perchpoint.current_org()
      AND principal.status = 'active'
      AND principal.revoked_at IS NULL
      AND (principal.expires_at IS NULL OR principal.expires_at > now())
      AND required = ANY(principal.capabilities)
  )
$$;

CREATE OR REPLACE FUNCTION perchpoint.property_authority_fact(target_property uuid)
RETURNS TABLE (
  monthly_budget_minor integer,
  monthly_rent_minor integer,
  source_kind text,
  source_reference text
)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT authority.monthly_budget_minor, authority.monthly_rent_minor,
         authority.source_kind, authority.source_reference
  FROM property_authority_limits authority
  WHERE authority.organization_id = perchpoint.current_org()
    AND authority.property_id = target_property
    AND authority.effective_at <= now()
    AND (authority.effective_until IS NULL OR authority.effective_until > now())
    AND (
      perchpoint.authorized_for('purchase.authorize', 'property', target_property)
      OR EXISTS (
        SELECT 1 FROM delegations delegation
        WHERE delegation.organization_id = authority.organization_id
          AND delegation.grantee_id = perchpoint.current_actor()
          AND delegation.capability = 'expense.approve'
          AND delegation.resource_type = 'property'
          AND delegation.resource_id = target_property
          AND delegation.amount_ceiling_minor IS NOT NULL
          AND cardinality(delegation.decision_types) > 0
          AND delegation.status = 'active'
          AND delegation.starts_at <= now()
          AND delegation.ends_at > now()
      )
    )
$$;

CREATE FUNCTION perchpoint.worker_assignment_allows(assignment uuid, property uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (
    SELECT 1 FROM worker_assignments work
    LEFT JOIN vendor_relationships relationship
      ON relationship.organization_id = work.organization_id
     AND relationship.id = work.vendor_relationship_id
    WHERE work.organization_id = perchpoint.current_org()
      AND work.status = 'active' AND work.starts_at <= now() AND work.ends_at > now()
      AND (
        work.vendor_relationship_id IS NULL
        OR (
          relationship.status = 'active'
          AND (relationship.ends_at IS NULL OR relationship.ends_at > now())
        )
      )
      AND work.worker_account_id = perchpoint.current_actor()
      AND (assignment IS NULL OR work.id = assignment)
      AND (property IS NULL OR work.property_id = property)
  )
$$;

CREATE OR REPLACE FUNCTION perchpoint.can_read_household(target uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT (
    perchpoint.authorized_for('household.read', 'household', target)
  ) OR EXISTS (
    SELECT 1 FROM portal_access access
    WHERE access.organization_id = perchpoint.current_org()
      AND access.household_id = target
      AND access.account_id = perchpoint.current_actor()
      AND access.effective_at <= now()
      AND (access.ended_at IS NULL OR access.ended_at > now())
  )
$$;

CREATE FUNCTION perchpoint.search_resource_allowed(kind text, resource uuid, classification text)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT CASE
    WHEN kind = 'property' THEN
      perchpoint.authorized_for('search.read', 'property', resource)
      AND perchpoint.authorized_for('property.read', 'property', resource)
      AND (
        classification <> 'restricted'
        OR perchpoint.authorized_for('security.read', 'property', resource)
        OR perchpoint.authorized_for('legal.read', 'property', resource)
      )
    WHEN kind = 'party' THEN
      perchpoint.authorized_for('search.read', 'organization', perchpoint.current_org())
      AND perchpoint.authorized_for('resident.read', 'organization', perchpoint.current_org())
      AND (
        classification <> 'restricted'
        OR perchpoint.authorized_for('security.read', 'organization', perchpoint.current_org())
        OR perchpoint.authorized_for('legal.read', 'organization', perchpoint.current_org())
      )
    WHEN kind = 'document' THEN EXISTS (
      SELECT 1 FROM documents document
      WHERE document.organization_id = perchpoint.current_org()
        AND document.id = resource
        AND perchpoint.authorized_for(
          'search.read', document.primary_resource_type, document.primary_resource_id
        )
        AND perchpoint.authorized_for(
          'document.read', document.primary_resource_type, document.primary_resource_id
        )
        AND (
          classification <> 'restricted'
          OR perchpoint.authorized_for(
            'security.read', document.primary_resource_type, document.primary_resource_id
          )
          OR perchpoint.authorized_for(
            'legal.read', document.primary_resource_type, document.primary_resource_id
          )
        )
    )
    WHEN kind = 'listing' THEN EXISTS (
      SELECT 1
      FROM listings listing
      JOIN spaces space
        ON space.organization_id = listing.organization_id
       AND space.id = listing.space_id
      WHERE listing.organization_id = perchpoint.current_org()
        AND listing.id = resource
        AND perchpoint.authorized_for('search.read', 'property', space.property_id)
        AND perchpoint.authorized_for('property.read', 'property', space.property_id)
        AND (
          classification <> 'restricted'
          OR perchpoint.authorized_for('security.read', 'property', space.property_id)
          OR perchpoint.authorized_for('legal.read', 'property', space.property_id)
        )
    )
    ELSE false
  END
$$;

CREATE OR REPLACE FUNCTION perchpoint.search_rows(query text, needle text, prefix text, contains text)
RETURNS TABLE (resource_type text, resource_id uuid, title text, classification text, rank integer)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT document.resource_type, document.resource_id, document.title, document.classification,
         CASE
           WHEN document.resource_id::text = query THEN 100
           WHEN document.title ILIKE needle THEN 80
           WHEN document.title ILIKE prefix THEN 60
           WHEN document.search_vector @@ websearch_to_tsquery('simple', query) THEN 40
           ELSE 20
         END AS rank
  FROM search_documents document
  WHERE document.organization_id = perchpoint.current_org()
    AND perchpoint.search_resource_allowed(
      document.resource_type, document.resource_id, document.classification
    )
    AND (
      document.resource_id::text = query
      OR document.title ILIKE needle
      OR document.title ILIKE prefix
      OR document.search_vector @@ websearch_to_tsquery('simple', query)
      OR document.title ILIKE contains
    )
  ORDER BY rank DESC, document.title
  LIMIT 20
$$;

CREATE OR REPLACE FUNCTION perchpoint.search_facets(query text, needle text, prefix text, contains text)
RETURNS TABLE (resource_type text, total bigint)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT document.resource_type, count(*)
  FROM search_documents document
  WHERE document.organization_id = perchpoint.current_org()
    AND perchpoint.search_resource_allowed(
      document.resource_type, document.resource_id, document.classification
    )
    AND (
      document.resource_id::text = query
      OR document.title ILIKE needle
      OR document.title ILIKE prefix
      OR document.search_vector @@ websearch_to_tsquery('simple', query)
      OR document.title ILIKE contains
    )
  GROUP BY document.resource_type
$$;

CREATE FUNCTION perchpoint.rebuild_search_projection(target_org uuid)
RETURNS TABLE (expected_count bigint, actual_count bigint)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  IF target_org <> perchpoint.current_org()
     OR NOT perchpoint.has_capability('platform.configure') THEN
    RAISE EXCEPTION 'projection_authority_required' USING ERRCODE = '42501';
  END IF;
  PERFORM pg_advisory_xact_lock(hashtextextended(target_org::text, 0));
  DELETE FROM search_documents WHERE organization_id = target_org;
  INSERT INTO search_documents (
    organization_id, id, resource_type, resource_id, title, body, classification
  )
  SELECT organization_id, gen_random_uuid(), 'party', id, display_name, party_kind, 'internal'
  FROM parties WHERE organization_id = target_org
  UNION ALL
  SELECT organization_id, gen_random_uuid(), 'property', id, name, property_type, 'internal'
  FROM properties WHERE organization_id = target_org
  UNION ALL
  SELECT organization_id, gen_random_uuid(), 'listing', id,
         property_name || ' ' || label, publication,
         CASE WHEN publication = 'published' THEN 'public' ELSE 'internal' END
  FROM listings WHERE organization_id = target_org
  UNION ALL
  SELECT document.organization_id, gen_random_uuid(), 'document', document.id,
         document.title, coalesce(artifact.extracted_text, ''), document.classification
  FROM documents document
  LEFT JOIN LATERAL (
    SELECT extracted_text FROM document_artifacts
    WHERE document_id = document.id AND artifact_kind = 'ocr' AND status = 'ready'
    ORDER BY created_at DESC LIMIT 1
  ) artifact ON true
  WHERE document.organization_id = target_org
    AND document.lifecycle = 'available'
    AND document.classification <> 'restricted';
  SELECT count(*) INTO actual_count
  FROM search_documents WHERE organization_id = target_org;
  SELECT
    (SELECT count(*) FROM parties WHERE organization_id = target_org) +
    (SELECT count(*) FROM properties WHERE organization_id = target_org) +
    (SELECT count(*) FROM listings WHERE organization_id = target_org) +
    (SELECT count(*) FROM documents
      WHERE organization_id = target_org
        AND lifecycle = 'available' AND classification <> 'restricted')
  INTO expected_count;
  RETURN NEXT;
END;
$$;

CREATE FUNCTION perchpoint.authenticate_service_credential(
  presented_hash text, expected_audience text, worker_name text
)
RETURNS TABLE (principal_id uuid, organization_id uuid, audience text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
BEGIN
  RETURN QUERY
  UPDATE service_credentials credential
  SET last_used_at = now()
  FROM service_principals principal
  WHERE credential.principal_id = principal.id
    AND credential.organization_id = principal.organization_id
    AND credential.verifier_hash = presented_hash
    AND credential.revoked_at IS NULL
    AND credential.expires_at > now()
    AND principal.status = 'active'
    AND principal.revoked_at IS NULL
    AND (principal.expires_at IS NULL OR principal.expires_at > now())
    AND principal.interactive = false
    AND principal.audience = expected_audience
    AND credential.bound_worker_name = worker_name
  RETURNING principal.id, principal.organization_id, principal.audience;
END;
$$;

CREATE OR REPLACE FUNCTION perchpoint.claim_document_job(worker text)
RETURNS TABLE (organization_id uuid, actor_id uuid, job_id uuid, document_id uuid, job_kind text)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE claimed document_jobs%ROWTYPE;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM service_principals principal
    WHERE principal.id = perchpoint.current_actor()
      AND principal.organization_id = perchpoint.current_org()
      AND principal.name = worker
      AND principal.status = 'active'
      AND principal.revoked_at IS NULL
      AND (principal.expires_at IS NULL OR principal.expires_at > now())
      AND 'document.process' = ANY(principal.capabilities)
  ) THEN
    RAISE EXCEPTION 'worker_authority_required' USING ERRCODE = '42501';
  END IF;
  SELECT job.* INTO claimed FROM document_jobs job
  WHERE job.organization_id = perchpoint.current_org()
    AND job.status IN ('pending', 'leased')
    AND job.available_at <= now()
    AND (job.lease_until IS NULL OR job.lease_until < now())
  ORDER BY job.created_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN RETURN; END IF;
  UPDATE document_jobs AS target_job
  SET status = 'leased', lease_until = now() + interval '60 seconds',
      attempts = target_job.attempts + 1
  WHERE target_job.id = claimed.id
    AND target_job.organization_id = perchpoint.current_org();
  RETURN QUERY SELECT claimed.organization_id, claimed.actor_id, claimed.id,
                      claimed.document_id, claimed.job_kind;
END
$$;

CREATE OR REPLACE FUNCTION perchpoint.claim_outbox(worker text)
RETURNS TABLE (id uuid, organization_id uuid, attempts integer, payload jsonb)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE claimed outbox%ROWTYPE;
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM service_principals principal
    WHERE principal.id = perchpoint.current_actor()
      AND principal.organization_id = perchpoint.current_org()
      AND principal.name = worker
      AND principal.status = 'active'
      AND principal.revoked_at IS NULL
      AND (principal.expires_at IS NULL OR principal.expires_at > now())
      AND 'outbox.deliver' = ANY(principal.capabilities)
  ) THEN
    RAISE EXCEPTION 'worker_authority_required' USING ERRCODE = '42501';
  END IF;
  SELECT pending.* INTO claimed FROM outbox pending
  WHERE pending.organization_id = perchpoint.current_org()
    AND pending.status IN ('pending', 'claimed')
    AND pending.available_at <= now()
    AND (pending.lease_until IS NULL OR pending.lease_until < now())
  ORDER BY pending.available_at
  FOR UPDATE SKIP LOCKED
  LIMIT 1;
  IF NOT FOUND THEN RETURN; END IF;
  IF claimed.attempts >= 5 THEN
    UPDATE outbox AS target_outbox
    SET status = 'dead_letter', last_error = 'attempt limit'
    WHERE target_outbox.id = claimed.id
      AND target_outbox.organization_id = perchpoint.current_org();
    RETURN QUERY SELECT claimed.id, claimed.organization_id, claimed.attempts, claimed.payload;
    RETURN;
  END IF;
  UPDATE outbox AS target_outbox
  SET status = 'claimed', claimed_by = worker, lease_until = now() + interval '30 seconds',
      attempts = target_outbox.attempts + 1
  WHERE target_outbox.id = claimed.id
    AND target_outbox.organization_id = perchpoint.current_org();
  RETURN QUERY SELECT claimed.id, claimed.organization_id, claimed.attempts + 1, claimed.payload;
END
$$;

CREATE OR REPLACE FUNCTION perchpoint.finish_outbox(target uuid, delivered boolean)
RETURNS text
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE worker text;
BEGIN
  SELECT principal.name INTO worker
  FROM service_principals principal
  WHERE principal.id = perchpoint.current_actor()
    AND principal.organization_id = perchpoint.current_org()
    AND principal.status = 'active'
    AND principal.revoked_at IS NULL
    AND (principal.expires_at IS NULL OR principal.expires_at > now())
    AND 'outbox.deliver' = ANY(principal.capabilities);
  IF worker IS NULL THEN
    RAISE EXCEPTION 'worker_authority_required' USING ERRCODE = '42501';
  END IF;
  IF delivered THEN
    UPDATE outbox SET status = 'delivered', lease_until = NULL
    WHERE id = target AND organization_id = perchpoint.current_org()
      AND status = 'claimed' AND claimed_by = worker;
    RETURN 'delivered';
  END IF;
  UPDATE outbox
  SET status = 'pending', available_at = now() + interval '1 second',
      last_error = 'synthetic rejection', lease_until = NULL
  WHERE id = target AND organization_id = perchpoint.current_org()
    AND status = 'claimed' AND claimed_by = worker;
  RETURN 'retry';
END
$$;

CREATE FUNCTION perchpoint.schedule_access_review(target_org uuid, reason text)
RETURNS uuid
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE campaign uuid := gen_random_uuid();
BEGIN
  INSERT INTO access_review_campaigns (
    organization_id, id, title, opens_at, due_at, trigger_kind, policy_version
  ) VALUES (
    target_org, campaign, 'Material-change access review: ' || left(reason, 120),
    now(), now() + interval '7 days', 'material_change', 'phase6-2'
  );
  INSERT INTO access_review_items (organization_id, id, campaign_id, account_id, status)
  SELECT target_org, gen_random_uuid(), campaign, membership.account_id, 'pending'
  FROM memberships membership
  WHERE membership.organization_id = target_org
    AND membership.effective_at <= now()
    AND (membership.ended_at IS NULL OR membership.ended_at > now());
  RETURN campaign;
END;
$$;

CREATE OR REPLACE FUNCTION perchpoint.quarterly_access_reviews()
RETURNS integer
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE created integer := 0; target uuid;
BEGIN
  FOR target IN SELECT id FROM organizations LOOP
    IF NOT EXISTS (
      SELECT 1 FROM access_review_campaigns campaign
      WHERE campaign.organization_id = target
        AND campaign.trigger_kind = 'quarterly'
        AND campaign.opens_at >= now() - interval '3 months'
    ) THEN
      INSERT INTO access_review_campaigns (
        organization_id, id, title, opens_at, due_at, trigger_kind, policy_version
      ) VALUES (
        target, gen_random_uuid(), 'Quarterly privileged access review',
        now(), now() + interval '14 days', 'quarterly', 'phase6-2'
      ) RETURNING id INTO target;
      INSERT INTO access_review_items (organization_id, id, campaign_id, account_id, status)
      SELECT organization_id, gen_random_uuid(), target, account_id, 'pending'
      FROM memberships
      WHERE organization_id = (
        SELECT organization_id FROM access_review_campaigns WHERE id = target
      )
        AND effective_at <= now() AND (ended_at IS NULL OR ended_at > now());
      created := created + 1;
    END IF;
  END LOOP;
  RETURN created;
END;
$$;

CREATE FUNCTION perchpoint.note_material_access_change()
RETURNS trigger
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE target_org uuid;
BEGIN
  target_org := COALESCE(NEW.organization_id, OLD.organization_id);
  PERFORM perchpoint.schedule_access_review(
    target_org,
    TG_TABLE_NAME || ':' || TG_OP
  );
  RETURN NEW;
END;
$$;

CREATE TRIGGER membership_material_access_review
AFTER INSERT OR UPDATE OF role_name, ended_at ON memberships
FOR EACH ROW EXECUTE FUNCTION perchpoint.note_material_access_change();
CREATE TRIGGER membership_scope_material_access_review
AFTER INSERT OR UPDATE OF ended_at ON membership_scope_assignments
FOR EACH ROW EXECUTE FUNCTION perchpoint.note_material_access_change();
CREATE TRIGGER worker_assignment_material_access_review
AFTER INSERT OR UPDATE OF status, ends_at ON worker_assignments
FOR EACH ROW EXECUTE FUNCTION perchpoint.note_material_access_change();

DROP POLICY IF EXISTS tenant_all ON properties;
CREATE POLICY property_capability_scope ON properties
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.authorized_for('property.read', 'property', id)
      OR perchpoint.worker_assignment_allows(NULL, id)
    )
  )
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.authorized_for('property.manage', 'property', id));

DROP POLICY IF EXISTS tenant_all ON buildings;
CREATE POLICY building_capability_scope ON buildings
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.authorized_for('property.read', 'property', property_id)
      OR perchpoint.worker_assignment_allows(NULL, property_id)
    )
  )
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.authorized_for('property.manage', 'property', property_id));

DROP POLICY IF EXISTS tenant_all ON spaces;
CREATE POLICY space_capability_scope ON spaces
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.authorized_for('property.read', 'property', property_id)
      OR perchpoint.worker_assignment_allows(NULL, property_id)
    )
  )
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.authorized_for('property.manage', 'property', property_id));

DROP POLICY IF EXISTS tenant_all ON parties;
CREATE POLICY party_capability_scope ON parties
  USING (organization_id = perchpoint.current_org() AND perchpoint.authorized_for('resident.read', 'organization', organization_id))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.authorized_for('party.create', 'organization', organization_id));

DROP POLICY IF EXISTS tenant_all ON listings;
CREATE POLICY listing_capability_scope ON listings
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.read', 'organization', organization_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.manage', 'organization', organization_id)
  );

DROP POLICY IF EXISTS tenant_all ON inquiries;
CREATE POLICY inquiry_capability_scope ON inquiries
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('inquiry.manage', 'organization', organization_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('inquiry.manage', 'organization', organization_id)
  );

DROP POLICY IF EXISTS tenant_all ON ownership_relationships;
CREATE POLICY ownership_relationship_scope ON ownership_relationships
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.read', 'property', property_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.manage', 'property', property_id)
  );

DROP POLICY IF EXISTS tenant_all ON management_relationships;
CREATE POLICY management_relationship_scope ON management_relationships
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.read', 'property', property_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.manage', 'property', property_id)
  );

DROP POLICY IF EXISTS tenant_all ON property_addresses;
CREATE POLICY property_address_scope ON property_addresses
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.read', 'property', property_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.manage', 'property', property_id)
  );

DROP POLICY IF EXISTS tenant_all ON parcels;
CREATE POLICY parcel_scope ON parcels
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.read', 'property', property_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.manage', 'property', property_id)
  );

DROP POLICY IF EXISTS tenant_all ON property_facts;
CREATE POLICY property_fact_scope ON property_facts
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.read', 'property', property_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.manage', 'property', property_id)
  );

DROP POLICY IF EXISTS tenant_all ON property_issues;
CREATE POLICY property_issue_scope ON property_issues
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.read', 'property', property_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('property.manage', 'property', property_id)
  );

DROP POLICY IF EXISTS tenant_all ON party_relationships;
CREATE POLICY party_relationship_scope ON party_relationships
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('resident.read', 'organization', organization_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('resident.read', 'organization', organization_id)
  );

DROP POLICY IF EXISTS tenant_all ON activity;
CREATE POLICY activity_capability_scope ON activity
  USING (
    organization_id = perchpoint.current_org()
    AND (
      actor_id = perchpoint.current_actor()
      OR perchpoint.has_capability('audit.read')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND actor_id = perchpoint.current_actor()
  );

DROP POLICY IF EXISTS tenant_all ON documents;
CREATE POLICY document_capability_scope ON documents
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('document.read', primary_resource_type, primary_resource_id)
    AND (classification <> 'restricted' OR perchpoint.has_capability('legal.read') OR perchpoint.has_capability('security.read'))
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('document.manage', primary_resource_type, primary_resource_id)
    AND classification <> 'restricted'
  );

DROP POLICY IF EXISTS tenant_all ON document_versions;
CREATE POLICY document_version_scope ON document_versions
  USING (
    organization_id = perchpoint.current_org()
    AND EXISTS (
      SELECT 1 FROM documents source
      WHERE source.organization_id = document_versions.organization_id
        AND source.id = document_versions.document_id
        AND perchpoint.authorized_for(
          'document.read', source.primary_resource_type, source.primary_resource_id
        )
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND EXISTS (
      SELECT 1 FROM documents source
      WHERE source.organization_id = document_versions.organization_id
        AND source.id = document_versions.document_id
        AND perchpoint.authorized_for(
          'document.manage', source.primary_resource_type, source.primary_resource_id
        )
    )
  );

DROP POLICY IF EXISTS tenant_all ON legal_holds;
CREATE POLICY legal_hold_scope ON legal_holds
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.has_capability('legal.read')
      OR perchpoint.has_capability('document.manage')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND placed_by = perchpoint.current_actor()
    AND (
      perchpoint.has_capability('legal.read')
      OR perchpoint.has_capability('document.manage')
    )
  );

DROP POLICY IF EXISTS tenant_all ON retention_policies;
CREATE POLICY retention_policy_scope ON retention_policies
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('legal.read')
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('legal.read')
  );

DROP POLICY IF EXISTS tenant_all ON document_jobs;
CREATE POLICY document_job_authority_scope ON document_jobs
  USING (
    organization_id = perchpoint.current_org()
    AND (
      actor_id = perchpoint.current_actor()
      OR perchpoint.has_capability('document.process')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND (
      actor_id = perchpoint.current_actor()
      OR perchpoint.has_capability('document.process')
    )
  );

DROP POLICY IF EXISTS tenant_all ON document_artifacts;
CREATE POLICY document_artifact_authority_scope ON document_artifacts
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.has_capability('document.process')
      OR EXISTS (
        SELECT 1 FROM documents source
        WHERE source.organization_id = document_artifacts.organization_id
          AND source.id = document_artifacts.document_id
          AND perchpoint.authorized_for(
            'document.read', source.primary_resource_type, source.primary_resource_id
          )
      )
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.has_capability('document.process')
      OR EXISTS (
        SELECT 1 FROM documents source
        WHERE source.organization_id = document_artifacts.organization_id
          AND source.id = document_artifacts.document_id
          AND perchpoint.authorized_for(
            'document.manage', source.primary_resource_type, source.primary_resource_id
          )
      )
    )
  );

DROP POLICY IF EXISTS tenant_all ON search_documents;
CREATE POLICY search_capability_scope ON search_documents
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.search_resource_allowed(resource_type, resource_id, classification)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND (
      (
        perchpoint.has_capability('search.read')
        AND perchpoint.search_resource_allowed(resource_type, resource_id, classification)
      )
      OR perchpoint.has_capability('platform.configure')
    )
  );

DROP POLICY IF EXISTS tenant_all ON document_exports;
CREATE POLICY export_owner_scope ON document_exports
  USING (
    organization_id = perchpoint.current_org()
    AND actor_id = perchpoint.current_actor()
    AND perchpoint.has_capability('export.create')
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND actor_id = perchpoint.current_actor()
    AND perchpoint.has_capability('export.create')
  );

DO $$
DECLARE governed_table text;
BEGIN
  FOREACH governed_table IN ARRAY ARRAY[
    'import_batches', 'import_rows', 'quality_findings', 'import_effects', 'replay_runs'
  ]
  LOOP
    EXECUTE format('DROP POLICY IF EXISTS tenant_all ON %I', governed_table);
    EXECUTE format(
      'CREATE POLICY governed_data_admin ON %I '
      'USING (organization_id = perchpoint.current_org() AND '
      '(perchpoint.has_capability(''import.manage'') OR perchpoint.has_capability(''platform.configure''))) '
      'WITH CHECK (organization_id = perchpoint.current_org() AND '
      '(perchpoint.has_capability(''import.manage'') OR perchpoint.has_capability(''platform.configure'')))',
      governed_table
    );
  END LOOP;
END
$$;

DROP POLICY IF EXISTS tenant_all ON audit_digests;
CREATE POLICY audit_digest_scope ON audit_digests
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('audit.read')
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('audit.read')
  );

DROP POLICY IF EXISTS maintenance_case_scope ON maintenance_cases;
CREATE POLICY maintenance_case_assignment_scope ON maintenance_cases
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.authorized_for('maintenance.case.read', 'organization', organization_id)
      OR perchpoint.has_capability('work.assign')
        AND perchpoint.worker_assignment_allows(assignment_id, NULL)
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.authorized_for('maintenance.case.write', 'organization', organization_id)
      OR perchpoint.has_capability('maintenance.case.write')
        AND perchpoint.worker_assignment_allows(assignment_id, NULL)
    )
  );

DROP POLICY IF EXISTS worker_assignment_scope ON worker_assignments;
CREATE POLICY worker_assignment_capability_scope ON worker_assignments
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.has_capability('work.assign')
        AND perchpoint.worker_assignment_allows(id, property_id)
      OR perchpoint.authorized_for('work.assign', 'property', property_id)
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('work.assign', 'property', property_id)
  );

DROP POLICY IF EXISTS access_request_org ON access_requests;
CREATE POLICY access_request_read ON access_requests
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND (
      requester_id = perchpoint.current_actor()
      OR approver_id = perchpoint.current_actor()
      OR perchpoint.has_capability('access.approve')
      OR perchpoint.has_capability('security.read')
    )
  );
CREATE POLICY access_request_create ON access_requests
  FOR INSERT
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND requester_id = perchpoint.current_actor()
    AND perchpoint.actor_in_org(organization_id)
  );
CREATE POLICY access_request_decide ON access_requests
  FOR UPDATE
  USING (
    organization_id = perchpoint.current_org()
    AND (
      perchpoint.has_capability('access.approve')
      OR perchpoint.has_capability('approval.owner')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND approver_id = perchpoint.current_actor()
  );

DROP POLICY IF EXISTS tenant_all ON memberships;
CREATE POLICY membership_least_privilege ON memberships
  USING (
    organization_id = perchpoint.current_org()
    AND (account_id = perchpoint.current_actor() OR perchpoint.has_capability('membership.read'))
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND account_id <> perchpoint.current_actor()
    AND (
      perchpoint.has_capability('membership.grant')
      OR perchpoint.has_capability('role.manage')
      OR perchpoint.has_capability('scope.manage')
      OR (
        perchpoint.has_capability('access.approve')
        AND ended_at IS NOT NULL
      )
    )
  );

DROP POLICY IF EXISTS invitation_org ON identity_invitations;
CREATE POLICY invitation_least_privilege ON identity_invitations
  USING (
    organization_id = perchpoint.current_org()
    AND (inviter_id = perchpoint.current_actor() OR perchpoint.has_capability('invitation.create'))
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND inviter_id = perchpoint.current_actor()
    AND perchpoint.has_capability('invitation.create')
  );

DROP POLICY IF EXISTS delegation_org ON delegations;
CREATE POLICY delegation_least_privilege ON delegations
  USING (
    organization_id = perchpoint.current_org()
    AND (
      grantor_id = perchpoint.current_actor()
      OR grantee_id = perchpoint.current_actor()
      OR perchpoint.has_capability('security.read')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND grantor_id = perchpoint.current_actor()
    AND grantee_id <> perchpoint.current_actor()
    AND perchpoint.has_capability('delegation.grant')
  );

DROP POLICY IF EXISTS service_principal_org ON service_principals;
CREATE POLICY service_principal_management ON service_principals
  USING (
    organization_id = perchpoint.current_org()
    AND (id = perchpoint.current_actor() OR perchpoint.has_capability('service.manage'))
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('service.manage')
    AND interactive = false
  );

DROP POLICY IF EXISTS service_credential_org ON service_credentials;
CREATE POLICY service_credential_management ON service_credentials
  USING (
    organization_id = perchpoint.current_org()
    AND (principal_id = perchpoint.current_actor() OR perchpoint.has_capability('service.manage'))
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('service.manage')
  );

DROP POLICY IF EXISTS scope_org ON authorization_scopes;
CREATE POLICY authorization_scope_management ON authorization_scopes
  USING (
    organization_id = perchpoint.current_org()
    AND (perchpoint.has_capability('membership.read') OR perchpoint.has_capability('scope.manage'))
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('scope.manage')
  );

DROP POLICY IF EXISTS scope_assignment_org ON membership_scope_assignments;
CREATE POLICY scope_assignment_management ON membership_scope_assignments
  USING (
    organization_id = perchpoint.current_org()
    AND (
      membership_id = NULLIF(current_setting('app.membership_id', true), '')::uuid
      OR perchpoint.has_capability('membership.read')
      OR perchpoint.has_capability('scope.manage')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('scope.manage')
  );

DROP POLICY IF EXISTS recovery_org ON privileged_recoveries;
CREATE POLICY privileged_recovery_participants ON privileged_recoveries
  USING (
    organization_id = perchpoint.current_org()
    AND (
      subject_account = perchpoint.current_actor()
      OR initiator_account = perchpoint.current_actor()
      OR approver_account = perchpoint.current_actor()
      OR perchpoint.has_capability('security.read')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND (initiator_account = perchpoint.current_actor() OR approver_account = perchpoint.current_actor())
    AND subject_account <> perchpoint.current_actor()
  );

DROP POLICY IF EXISTS review_campaign_org ON access_review_campaigns;
CREATE POLICY review_campaign_security ON access_review_campaigns
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('security.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('access.approve'));

DROP POLICY IF EXISTS review_item_org ON access_review_items;
CREATE POLICY review_item_security ON access_review_items
  USING (
    organization_id = perchpoint.current_org()
    AND (
      account_id = perchpoint.current_actor()
      OR reviewer_id = perchpoint.current_actor()
      OR perchpoint.has_capability('security.read')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('access.approve')
    AND account_id <> perchpoint.current_actor()
  );

DROP POLICY IF EXISTS security_event_read ON security_events;
CREATE POLICY security_event_least_privilege ON security_events
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND (
      actor_account_id = perchpoint.current_actor()
      OR perchpoint.has_capability('security.read')
    )
  );

CREATE POLICY access_grant_scope ON access_grants
  USING (
    organization_id = perchpoint.current_org()
    AND (account_id = perchpoint.current_actor() OR perchpoint.has_capability('access.approve'))
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND approved_by = perchpoint.current_actor()
    AND account_id <> perchpoint.current_actor()
    AND perchpoint.has_capability('access.approve')
  );

CREATE POLICY authority_change_approval_read ON authority_change_approvals
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND (
      target_account_id = perchpoint.current_actor()
      OR approved_by = perchpoint.current_actor()
      OR perchpoint.has_capability('role.manage')
      OR perchpoint.has_capability('scope.manage')
    )
  );
CREATE POLICY authority_change_approval_create ON authority_change_approvals
  FOR INSERT
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND approved_by = perchpoint.current_actor()
    AND target_account_id <> perchpoint.current_actor()
    AND perchpoint.has_capability('approval.owner')
  );
CREATE POLICY authority_change_approval_consume ON authority_change_approvals
  FOR UPDATE
  USING (
    organization_id = perchpoint.current_org()
    AND (perchpoint.has_capability('role.manage') OR perchpoint.has_capability('scope.manage'))
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND consumed_by = perchpoint.current_actor()
    AND approved_by <> perchpoint.current_actor()
    AND target_account_id <> perchpoint.current_actor()
  );

CREATE POLICY business_action_scope ON authorized_business_actions
  USING (organization_id = perchpoint.current_org() AND actor_id = perchpoint.current_actor())
  WITH CHECK (organization_id = perchpoint.current_org() AND actor_id = perchpoint.current_actor());

CREATE POLICY review_remediation_scope ON access_review_remediations
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('security.read'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('security.read'));

CREATE POLICY property_authority_limit_scope ON property_authority_limits
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('purchase.authorize', 'property', property_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.authorized_for('approval.owner', 'property', property_id)
  );

CREATE POLICY privileged_recovery_event_read ON privileged_recovery_events
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('security.read')
  );

UPDATE identity_invitations
SET relationship_type = COALESCE(relationship_type, 'organization_membership'),
    relationship_id = COALESCE(relationship_id, organization_id),
    scope_payload = CASE
      WHEN scope_payload = '{}'::jsonb THEN jsonb_build_object(
        'type', 'organization',
        'resource_id', organization_id::text
      )
      ELSE scope_payload
    END;

ALTER TABLE identity_invitations
  ALTER COLUMN relationship_type SET NOT NULL,
  ALTER COLUMN relationship_id SET NOT NULL;

ALTER TABLE identity_invitations
  ADD CONSTRAINT identity_invitation_scope_bound
  CHECK (
    scope_payload ? 'type'
    AND scope_payload ? 'resource_id'
    AND length(scope_payload ->> 'type') > 0
    AND length(scope_payload ->> 'resource_id') > 0
  );

CREATE OR REPLACE FUNCTION perchpoint.validate_invitation_activation()
RETURNS trigger
LANGUAGE plpgsql
SET search_path = public, pg_temp
AS $$
BEGIN
  IF OLD.accepted_at IS NULL AND NEW.accepted_at IS NOT NULL THEN
    IF NEW.relationship_type IS NULL
       OR NEW.relationship_id IS NULL
       OR NOT (NEW.scope_payload ? 'type' AND NEW.scope_payload ? 'resource_id') THEN
      RAISE EXCEPTION 'invitation_binding_invalid';
    END IF;
    IF NEW.relationship_type = 'vendor_worker_proposal'
       AND NOT EXISTS (
         SELECT 1
         FROM vendor_worker_proposals proposal
         WHERE proposal.organization_id = NEW.organization_id
           AND proposal.id = NEW.relationship_id
           AND proposal.status = 'approved'
           AND proposal.invitation_id = NEW.id
       ) THEN
      RAISE EXCEPTION 'invitation_approval_invalid';
    END IF;
  END IF;
  RETURN NEW;
END
$$;

DROP TRIGGER IF EXISTS identity_invitation_activation_guard ON identity_invitations;
CREATE TRIGGER identity_invitation_activation_guard
BEFORE UPDATE OF accepted_at ON identity_invitations
FOR EACH ROW EXECUTE FUNCTION perchpoint.validate_invitation_activation();

REVOKE ALL ON FUNCTION perchpoint.role_for_account(uuid),
  perchpoint.access_directory(),
  perchpoint.has_capability(text), perchpoint.scope_allows(text, uuid),
  perchpoint.authorized_for(text, text, uuid),
  perchpoint.property_authority_fact(uuid),
  perchpoint.worker_assignment_allows(uuid, uuid), perchpoint.search_resource_allowed(text, uuid, text),
  perchpoint.resolve_authority_context(uuid, uuid, uuid),
  perchpoint.rebuild_search_projection(uuid),
  perchpoint.authenticate_service_credential(text, text, text),
  perchpoint.schedule_access_review(uuid, text), perchpoint.quarterly_access_reviews(),
  perchpoint.note_material_access_change() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.role_for_account(uuid),
  perchpoint.access_directory(),
  perchpoint.has_capability(text), perchpoint.scope_allows(text, uuid),
  perchpoint.authorized_for(text, text, uuid),
  perchpoint.property_authority_fact(uuid),
  perchpoint.worker_assignment_allows(uuid, uuid), perchpoint.search_resource_allowed(text, uuid, text),
  perchpoint.resolve_authority_context(uuid, uuid, uuid),
  perchpoint.rebuild_search_projection(uuid)
  TO perchpoint_runtime, perchpoint_definer;
GRANT EXECUTE ON FUNCTION perchpoint.authenticate_service_credential(text, text, text)
  TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.schedule_access_review(uuid, text),
  perchpoint.quarterly_access_reviews() TO perchpoint_runtime, perchpoint_definer;

CREATE INDEX access_grants_active_idx
  ON access_grants (organization_id, account_id, capability, ends_at)
  WHERE revoked_at IS NULL;
CREATE INDEX business_actions_idempotency_idx
  ON authorized_business_actions (organization_id, actor_id, idempotency_key);
CREATE INDEX service_credentials_verifier_idx
  ON service_credentials (verifier_hash) WHERE revoked_at IS NULL;

ALTER FUNCTION perchpoint.current_membership(uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.access_directory() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.role_for_account(uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.current_role() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.actor_in_org(uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.resolve_authority_context(uuid, uuid, uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.has_capability(text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.scope_allows(text, uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.authorized_for(text, text, uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.property_authority_fact(uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.worker_assignment_allows(uuid, uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.can_read_household(uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.search_resource_allowed(text, uuid, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.rebuild_search_projection(uuid) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.authenticate_service_credential(text, text, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.schedule_access_review(uuid, text) OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.quarterly_access_reviews() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.note_material_access_change() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.validate_invitation_activation() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.record_privileged_recovery_event() OWNER TO perchpoint_definer;
ALTER FUNCTION perchpoint.validate_delegation_bounds() OWNER TO perchpoint_definer;

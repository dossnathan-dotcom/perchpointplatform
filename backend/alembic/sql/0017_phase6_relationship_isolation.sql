CREATE TABLE vendor_relationships (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  vendor_name text NOT NULL,
  administrator_account_id uuid REFERENCES accounts(id),
  starts_at timestamptz NOT NULL DEFAULT now(),
  ends_at timestamptz,
  status text NOT NULL CHECK (status IN ('proposed', 'active', 'suspended', 'ended')),
  PRIMARY KEY (organization_id, id),
  CHECK (ends_at IS NULL OR ends_at > starts_at)
);

CREATE TABLE worker_assignments (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  vendor_relationship_id uuid,
  worker_account_id uuid NOT NULL REFERENCES accounts(id),
  property_id uuid REFERENCES properties(id),
  assignment_kind text NOT NULL CHECK (assignment_kind IN ('vendor', 'technician', 'cleaner')),
  minimum_resident_context jsonb NOT NULL DEFAULT '{}'::jsonb,
  starts_at timestamptz NOT NULL,
  ends_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('proposed', 'active', 'completed', 'cancelled', 'revoked')),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, vendor_relationship_id)
    REFERENCES vendor_relationships(organization_id, id),
  CHECK (ends_at > starts_at)
);

ALTER TABLE vendor_relationships ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_relationships FORCE ROW LEVEL SECURITY;
ALTER TABLE worker_assignments ENABLE ROW LEVEL SECURITY;
ALTER TABLE worker_assignments FORCE ROW LEVEL SECURITY;

CREATE FUNCTION perchpoint.current_role()
RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT role_name
  FROM memberships
  WHERE account_id = perchpoint.current_actor()
    AND organization_id = perchpoint.current_org()
    AND effective_at <= now()
    AND (ended_at IS NULL OR ended_at > now())
  ORDER BY effective_at DESC
  LIMIT 1
$$;

CREATE FUNCTION perchpoint.can_read_household(target uuid)
RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT CASE
    WHEN perchpoint.current_role() IN (
      'owner', 'project_manager', 'operations_manager', 'leasing', 'leasing_staff',
      'maintenance_coordinator', 'accounting', 'platform_admin'
    ) THEN true
    ELSE EXISTS (
      SELECT 1 FROM portal_access access
      WHERE access.organization_id = perchpoint.current_org()
        AND access.household_id = target
        AND access.account_id = perchpoint.current_actor()
        AND access.effective_at <= now()
        AND (access.ended_at IS NULL OR access.ended_at > now())
    )
  END
$$;

DROP POLICY tenant_all ON households;
CREATE POLICY household_relationship ON households
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND perchpoint.can_read_household(id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND perchpoint.current_role() IN ('owner', 'project_manager', 'operations_manager', 'leasing', 'leasing_staff')
  );

DROP POLICY tenant_all ON portal_access;
CREATE POLICY portal_access_relationship ON portal_access
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND (
      account_id = perchpoint.current_actor()
      OR perchpoint.current_role() IN ('owner', 'project_manager', 'operations_manager', 'leasing', 'leasing_staff')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND perchpoint.current_role() IN ('owner', 'project_manager', 'operations_manager', 'leasing', 'leasing_staff')
  );

CREATE POLICY vendor_relationship_scope ON vendor_relationships
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND (
      administrator_account_id = perchpoint.current_actor()
      OR perchpoint.current_role() IN ('owner', 'project_manager', 'operations_manager', 'maintenance_coordinator')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND perchpoint.current_role() IN ('owner', 'project_manager', 'operations_manager', 'maintenance_coordinator')
  );

CREATE POLICY worker_assignment_scope ON worker_assignments
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND (
      (
        worker_account_id = perchpoint.current_actor()
        AND status = 'active'
        AND starts_at <= now()
        AND ends_at > now()
      )
      OR perchpoint.current_role() IN ('owner', 'project_manager', 'operations_manager', 'maintenance_coordinator')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND perchpoint.current_role() IN ('owner', 'project_manager', 'operations_manager', 'maintenance_coordinator')
  );

REVOKE ALL ON FUNCTION perchpoint.current_role(), perchpoint.can_read_household(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.current_role(), perchpoint.can_read_household(uuid)
  TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT, UPDATE, DELETE ON vendor_relationships, worker_assignments
  TO perchpoint_runtime, perchpoint_definer;

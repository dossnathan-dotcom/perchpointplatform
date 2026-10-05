SET LOCAL ROLE perchpoint_definer;
INSERT INTO capabilities (code, family, description)
VALUES ('vendor.worker.approve', 'vendor', 'Approve proposed vendor workers')
ON CONFLICT (code) DO NOTHING;
RESET ROLE;

CREATE TABLE vendor_worker_proposals (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  vendor_relationship_id uuid NOT NULL,
  email text NOT NULL,
  role_name text NOT NULL CHECK (role_name IN ('vendor_worker', 'technician', 'cleaner')),
  property_id uuid REFERENCES properties(id),
  starts_at timestamptz NOT NULL,
  ends_at timestamptz NOT NULL,
  status text NOT NULL CHECK (status IN ('proposed', 'approved', 'activated', 'denied', 'revoked')),
  proposed_by uuid NOT NULL,
  decided_by uuid,
  decided_at timestamptz,
  invitation_id uuid,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, vendor_relationship_id)
    REFERENCES vendor_relationships(organization_id, id),
  CHECK (ends_at > starts_at),
  CHECK (decided_by IS NULL OR decided_by <> proposed_by)
);

ALTER TABLE vendor_worker_proposals ENABLE ROW LEVEL SECURITY;
ALTER TABLE vendor_worker_proposals FORCE ROW LEVEL SECURITY;

CREATE POLICY vendor_worker_proposal_scope ON vendor_worker_proposals
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND (
      proposed_by = perchpoint.current_actor()
      OR perchpoint.current_role() IN (
        'owner', 'project_manager', 'operations_manager', 'maintenance_coordinator'
      )
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
    AND (
      (
        proposed_by = perchpoint.current_actor()
        AND EXISTS (
          SELECT 1
          FROM vendor_relationships relationship
          WHERE relationship.organization_id = vendor_worker_proposals.organization_id
            AND relationship.id = vendor_worker_proposals.vendor_relationship_id
            AND relationship.administrator_account_id = perchpoint.current_actor()
            AND relationship.status = 'active'
        )
      )
      OR perchpoint.current_role() IN (
        'owner', 'project_manager', 'operations_manager', 'maintenance_coordinator'
      )
    )
  );

GRANT SELECT, INSERT, UPDATE ON vendor_worker_proposals
  TO perchpoint_runtime, perchpoint_definer;

CREATE FUNCTION perchpoint.activate_vendor_worker(target_account uuid, target_email text)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  proposal vendor_worker_proposals%ROWTYPE;
  assignment_id uuid;
BEGIN
  SELECT candidate.*
  INTO proposal
  FROM vendor_worker_proposals candidate
  JOIN identity_invitations invitation
    ON invitation.organization_id = candidate.organization_id
   AND invitation.id = candidate.invitation_id
  WHERE lower(candidate.email) = lower(target_email)
    AND candidate.status = 'approved'
    AND invitation.accepted_at IS NOT NULL
  ORDER BY candidate.created_at DESC
  LIMIT 1
  FOR UPDATE OF candidate;

  IF proposal.id IS NULL THEN
    RETURN NULL;
  END IF;

  assignment_id := gen_random_uuid();
  INSERT INTO worker_assignments (
    organization_id, id, vendor_relationship_id, worker_account_id,
    property_id, assignment_kind, starts_at, ends_at, status
  ) VALUES (
    proposal.organization_id,
    assignment_id,
    proposal.vendor_relationship_id,
    target_account,
    proposal.property_id,
    CASE
      WHEN proposal.role_name = 'cleaner' THEN 'cleaner'
      WHEN proposal.role_name = 'technician' THEN 'technician'
      ELSE 'vendor'
    END,
    proposal.starts_at,
    proposal.ends_at,
    'active'
  );

  UPDATE vendor_worker_proposals
  SET status = 'activated'
  WHERE organization_id = proposal.organization_id
    AND id = proposal.id;

  RETURN assignment_id;
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.activate_vendor_worker(uuid, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.activate_vendor_worker(uuid, text)
  TO perchpoint_runtime;

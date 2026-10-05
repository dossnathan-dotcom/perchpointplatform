CREATE TABLE identity_lifecycle_events (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  account_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  action text NOT NULL CHECK (action IN ('suspended', 'restored')),
  reason text NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

ALTER TABLE identity_lifecycle_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE identity_lifecycle_events FORCE ROW LEVEL SECURITY;

CREATE POLICY identity_lifecycle_org ON identity_lifecycle_events
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND actor_id = perchpoint.current_actor()
  );

GRANT SELECT, INSERT ON identity_lifecycle_events
  TO perchpoint_runtime, perchpoint_definer;
REVOKE UPDATE, DELETE ON identity_lifecycle_events FROM perchpoint_runtime;

CREATE FUNCTION perchpoint.set_identity_lifecycle(
  acting_account uuid,
  target_account uuid,
  target_org uuid,
  lifecycle_action text,
  lifecycle_reason text
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  actor_role text;
  target_identity uuid;
  session_count integer := 0;
  membership_count integer := 0;
  delegation_count integer := 0;
  assignment_count integer := 0;
BEGIN
  IF acting_account = target_account THEN
    RAISE EXCEPTION 'self_lifecycle_change' USING ERRCODE = '42501';
  END IF;

  SELECT role_name INTO actor_role
  FROM memberships
  WHERE account_id = acting_account
    AND organization_id = target_org
    AND effective_at <= now()
    AND (ended_at IS NULL OR ended_at > now())
  ORDER BY effective_at DESC
  LIMIT 1;

  IF actor_role NOT IN ('owner', 'platform_admin') THEN
    RAISE EXCEPTION 'lifecycle_authority_required' USING ERRCODE = '42501';
  END IF;

  SELECT id INTO target_identity
  FROM identity_accounts
  WHERE account_id = target_account;

  IF target_identity IS NULL THEN
    RAISE EXCEPTION 'identity_missing' USING ERRCODE = 'P0002';
  END IF;

  IF lifecycle_action = 'suspended' THEN
    UPDATE identity_accounts
    SET status = 'suspended'
    WHERE id = target_identity
      AND status = 'active';
    IF NOT FOUND THEN
      RAISE EXCEPTION 'identity_not_active' USING ERRCODE = 'P0002';
    END IF;

    UPDATE identity_sessions
    SET revoked_at = now(), revoke_reason = 'identity_suspended'
    WHERE identity_id = target_identity
      AND revoked_at IS NULL;
    GET DIAGNOSTICS session_count = ROW_COUNT;

    UPDATE memberships
    SET ended_at = now()
    WHERE account_id = target_account
      AND organization_id = target_org
      AND effective_at <= now()
      AND (ended_at IS NULL OR ended_at > now());
    GET DIAGNOSTICS membership_count = ROW_COUNT;

    UPDATE delegations
    SET status = 'revoked', revoked_at = now()
    WHERE organization_id = target_org
      AND status = 'active'
      AND (grantor_id = target_account OR grantee_id = target_account);
    GET DIAGNOSTICS delegation_count = ROW_COUNT;

    UPDATE worker_assignments
    SET status = 'revoked'
    WHERE organization_id = target_org
      AND worker_account_id = target_account
      AND status IN ('proposed', 'active');
    GET DIAGNOSTICS assignment_count = ROW_COUNT;
  ELSIF lifecycle_action = 'restored' THEN
    UPDATE identity_accounts
    SET status = 'active'
    WHERE id = target_identity
      AND status = 'suspended';
    IF NOT FOUND THEN
      RAISE EXCEPTION 'identity_not_suspended' USING ERRCODE = 'P0002';
    END IF;
  ELSE
    RAISE EXCEPTION 'lifecycle_action_invalid' USING ERRCODE = '22023';
  END IF;

  INSERT INTO identity_lifecycle_events (
    organization_id, id, account_id, actor_id, action, reason, details
  ) VALUES (
    target_org,
    gen_random_uuid(),
    target_account,
    acting_account,
    lifecycle_action,
    lifecycle_reason,
    jsonb_build_object(
      'sessions_revoked', session_count,
      'memberships_ended', membership_count,
      'delegations_revoked', delegation_count,
      'assignments_revoked', assignment_count,
      'authority_restored', false
    )
  );

  RETURN jsonb_build_object(
    'action', lifecycle_action,
    'sessions_revoked', session_count,
    'memberships_ended', membership_count,
    'delegations_revoked', delegation_count,
    'assignments_revoked', assignment_count,
    'authority_restored', false
  );
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.set_identity_lifecycle(uuid, uuid, uuid, text, text)
  FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.set_identity_lifecycle(uuid, uuid, uuid, text, text)
  TO perchpoint_runtime;

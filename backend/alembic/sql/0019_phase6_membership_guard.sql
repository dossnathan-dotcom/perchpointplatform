CREATE OR REPLACE FUNCTION perchpoint.active_org_member(target_account uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT perchpoint.actor_in_org(perchpoint.current_org())
    AND EXISTS (
      SELECT 1
      FROM memberships
      WHERE account_id = target_account
        AND organization_id = perchpoint.current_org()
        AND effective_at <= now()
        AND (ended_at IS NULL OR ended_at > now())
    )
$$;

REVOKE ALL ON FUNCTION perchpoint.active_org_member(uuid) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.active_org_member(uuid) TO perchpoint_runtime;

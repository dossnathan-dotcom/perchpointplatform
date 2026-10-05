CREATE OR REPLACE FUNCTION perchpoint.access_directory()
RETURNS TABLE (
  account_id uuid,
  email text,
  membership_id uuid,
  role_name text
)
LANGUAGE sql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT a.id, a.email, m.id, m.role_name
  FROM memberships m
  JOIN accounts a ON a.id = m.account_id
  WHERE m.organization_id = perchpoint.current_org()
    AND m.effective_at <= now()
    AND (m.ended_at IS NULL OR m.ended_at > now())
    AND perchpoint.current_role() IN (
      'owner', 'platform_admin', 'project_manager', 'operations_manager'
    )
  ORDER BY a.email
$$;

REVOKE ALL ON FUNCTION perchpoint.access_directory() FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.access_directory() TO perchpoint_runtime;

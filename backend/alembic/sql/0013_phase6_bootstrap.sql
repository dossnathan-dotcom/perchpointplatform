CREATE OR REPLACE FUNCTION perchpoint.claim_invitation(token_hash text)
RETURNS TABLE (organization_id uuid, invitation_id uuid, email text, role_name text, inviter_id uuid, expires_at timestamptz, accepted_at timestamptz, revoked_at timestamptz)
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT organization_id, id, email, role_name, inviter_id, expires_at, accepted_at, revoked_at
  FROM identity_invitations
  WHERE identity_invitations.token_hash = claim_invitation.token_hash
$$;

REVOKE ALL ON FUNCTION perchpoint.claim_invitation(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.claim_invitation(text) TO perchpoint_runtime;

CREATE OR REPLACE FUNCTION perchpoint.accept_invitation(token_hash text)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE updated int;
BEGIN
  UPDATE identity_invitations
  SET accepted_at = now()
  WHERE identity_invitations.token_hash = accept_invitation.token_hash
    AND accepted_at IS NULL
    AND revoked_at IS NULL
    AND expires_at > now();
  GET DIAGNOSTICS updated = ROW_COUNT;
  RETURN updated = 1;
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.accept_invitation(text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.accept_invitation(text) TO perchpoint_runtime;

DROP FUNCTION IF EXISTS perchpoint.accept_invitation(text);

CREATE FUNCTION perchpoint.accept_invitation(token_hash text, intended_email text)
RETURNS boolean
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE updated integer;
BEGIN
  UPDATE identity_invitations invitation
  SET accepted_at = now()
  WHERE invitation.token_hash = accept_invitation.token_hash
    AND lower(invitation.email) = lower(accept_invitation.intended_email)
    AND invitation.approval_status = 'approved'
    AND invitation.accepted_at IS NULL
    AND invitation.revoked_at IS NULL
    AND invitation.expires_at > now()
    AND EXISTS (
      SELECT 1 FROM memberships membership
      WHERE membership.account_id = invitation.inviter_id
        AND membership.organization_id = invitation.organization_id
        AND membership.effective_at <= now()
        AND (membership.ended_at IS NULL OR membership.ended_at > now())
    );
  GET DIAGNOSTICS updated = ROW_COUNT;
  RETURN updated = 1;
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.accept_invitation(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.accept_invitation(text, text) TO perchpoint_runtime;

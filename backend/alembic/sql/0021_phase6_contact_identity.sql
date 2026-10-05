CREATE OR REPLACE FUNCTION perchpoint.account_id_for_subject(lookup_subject text)
RETURNS uuid
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT account_id
  FROM identity_accounts
  WHERE provider_subject = $1
    AND status = 'active'
$$;

CREATE OR REPLACE FUNCTION perchpoint.sync_provider_email(lookup_subject text, confirmed_email text)
RETURNS uuid
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  target_account uuid;
  target_identity uuid;
  prior_email text;
BEGIN
  SELECT identity.account_id, identity.id, account.email
    INTO target_account, target_identity, prior_email
  FROM identity_accounts identity
  JOIN accounts account ON account.id = identity.account_id
  WHERE identity.provider_subject = $1
    AND identity.status = 'active';

  IF target_account IS NULL THEN
    RETURN NULL;
  END IF;

  IF lower(prior_email) <> lower(confirmed_email) THEN
    UPDATE accounts
    SET email = lower(confirmed_email)
    WHERE id = target_account;

    UPDATE identity_contact_history
    SET status = 'verified',
        verified_at = now()
    WHERE identity_id = target_identity
      AND contact_kind = 'email'
      AND lower(proposed_value) = lower(confirmed_email)
      AND status = 'pending';

    UPDATE identity_sessions
    SET revoked_at = now(),
        revoke_reason = 'verified_email_change'
    WHERE identity_id = target_identity
      AND revoked_at IS NULL;
  END IF;

  UPDATE identity_accounts
  SET email_verified = true
  WHERE id = target_identity;

  RETURN target_account;
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.account_id_for_subject(text) FROM PUBLIC;
REVOKE ALL ON FUNCTION perchpoint.sync_provider_email(text, text) FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.account_id_for_subject(text) TO perchpoint_runtime;
GRANT EXECUTE ON FUNCTION perchpoint.sync_provider_email(text, text) TO perchpoint_runtime;

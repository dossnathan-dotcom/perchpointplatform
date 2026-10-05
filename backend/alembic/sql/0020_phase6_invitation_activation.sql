ALTER TABLE identity_accounts
  ADD COLUMN mfa_required boolean NOT NULL DEFAULT false;

CREATE OR REPLACE FUNCTION perchpoint.activate_invitation(
  presented_token_hash text,
  intended_email text,
  immutable_provider_subject text,
  disabled_legacy_password_hash text
)
RETURNS TABLE (
  account_id uuid,
  organization_id uuid,
  role_name text,
  mfa_required boolean
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  invitation identity_invitations%ROWTYPE;
  target_account uuid;
  target_identity uuid;
  existing_subject text;
  require_mfa boolean;
BEGIN
  SELECT candidate.*
  INTO invitation
  FROM identity_invitations candidate
  WHERE candidate.token_hash = presented_token_hash
    AND lower(candidate.email) = lower(intended_email)
    AND candidate.approval_status = 'approved'
    AND candidate.accepted_at IS NULL
    AND candidate.revoked_at IS NULL
    AND candidate.expires_at > now()
    AND EXISTS (
      SELECT 1
      FROM memberships inviter_membership
      WHERE inviter_membership.account_id = candidate.inviter_id
        AND inviter_membership.organization_id = candidate.organization_id
        AND inviter_membership.effective_at <= now()
        AND (
          inviter_membership.ended_at IS NULL
          OR inviter_membership.ended_at > now()
        )
        AND candidate.role_name NOT IN ('owner', 'platform_admin')
        AND (
          (
            candidate.role_name IN (
              'applicant', 'resident', 'household_adult', 'guarantor',
              'vendor_admin', 'vendor_worker', 'technician', 'cleaner'
            )
            AND inviter_membership.role_name IN (
              'owner', 'platform_admin', 'project_manager', 'operations_manager',
              'leasing', 'leasing_staff', 'maintenance_coordinator'
            )
          )
          OR (
            candidate.role_name NOT IN (
              'applicant', 'resident', 'household_adult', 'guarantor',
              'vendor_admin', 'vendor_worker', 'technician', 'cleaner'
            )
            AND inviter_membership.role_name IN ('owner', 'platform_admin')
          )
        )
    )
  FOR UPDATE;

  IF invitation.id IS NULL THEN
    RETURN;
  END IF;

  SELECT id INTO target_account
  FROM accounts
  WHERE lower(email) = lower(intended_email);

  IF target_account IS NULL THEN
    target_account := gen_random_uuid();
    INSERT INTO accounts (id, email, password_hash, synthetic)
    VALUES (
      target_account,
      lower(intended_email),
      disabled_legacy_password_hash,
      true
    );
  END IF;

  SELECT id, provider_subject
  INTO target_identity, existing_subject
  FROM identity_accounts
  WHERE identity_accounts.account_id = target_account;

  IF existing_subject IS NOT NULL
     AND existing_subject <> immutable_provider_subject THEN
    RAISE EXCEPTION 'invitation_identity_mismatch';
  END IF;

  require_mfa := invitation.role_name IN (
    'owner', 'platform_admin', 'project_manager', 'operations_manager',
    'leasing', 'leasing_staff', 'maintenance', 'maintenance_coordinator',
    'accounting', 'limited_approver', 'vendor_admin', 'vendor_worker',
    'technician', 'cleaner'
  );

  IF target_identity IS NULL THEN
    target_identity := gen_random_uuid();
    INSERT INTO identity_accounts (
      id, account_id, provider_subject, status, email_verified, mfa_required
    ) VALUES (
      target_identity,
      target_account,
      immutable_provider_subject,
      'active',
      true,
      require_mfa
    );
  ELSE
    UPDATE identity_accounts
    SET email_verified = true,
        mfa_required = identity_accounts.mfa_required OR require_mfa
    WHERE id = target_identity;
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM memberships
    WHERE memberships.account_id = target_account
      AND memberships.organization_id = invitation.organization_id
      AND memberships.role_name = invitation.role_name
      AND memberships.effective_at <= now()
      AND (
        memberships.ended_at IS NULL
        OR memberships.ended_at > now()
      )
  ) THEN
    INSERT INTO memberships (
      id, account_id, organization_id, role_name, effective_at
    ) VALUES (
      gen_random_uuid(),
      target_account,
      invitation.organization_id,
      invitation.role_name,
      now()
    );
  END IF;

  UPDATE identity_invitations
  SET accepted_at = now(), accepted_identity_id = target_identity
  WHERE identity_invitations.organization_id = invitation.organization_id
    AND identity_invitations.id = invitation.id;

  RETURN QUERY
  SELECT
    target_account,
    invitation.organization_id,
    invitation.role_name,
    require_mfa;
END;
$$;

REVOKE ALL ON FUNCTION perchpoint.activate_invitation(text, text, text, text)
  FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.activate_invitation(text, text, text, text)
  TO perchpoint_runtime;

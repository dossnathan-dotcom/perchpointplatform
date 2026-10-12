"""Additional payers authenticate individually without a workforce MFA requirement."""
from alembic import op

revision = "0050_phase17_payer_mfa"
down_revision = "0049_phase17_additional_payer"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION perchpoint.record_provider_session(
          account uuid, subject text, org uuid, token_hash text, csrf_hash text,
          assurance text, device text, idle_until timestamptz, absolute_until timestamptz,
          idle_seconds integer, provider_session text, refresh_ciphertext text
        ) RETURNS uuid
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        DECLARE
          identity uuid;
          session_id uuid := gen_random_uuid();
          require_mfa boolean;
        BEGIN
          SELECT EXISTS (
            SELECT 1
            FROM memberships membership
            WHERE membership.account_id = account
              AND membership.organization_id = org
              AND membership.effective_at <= now()
              AND (membership.ended_at IS NULL OR membership.ended_at > now())
              AND membership.role_name NOT IN (
                'applicant', 'resident', 'household_adult', 'guarantor', 'additional_payer', 'service_principal'
              )
          ) INTO require_mfa;

          SELECT id INTO identity FROM identity_accounts WHERE account_id = account;
          IF identity IS NULL THEN
            identity := gen_random_uuid();
            INSERT INTO identity_accounts (
              id, account_id, provider_subject, status, email_verified, assurance, mfa_required
            )
            VALUES (
              identity, account, subject, 'active', true, assurance, require_mfa
            );
          ELSE
            IF EXISTS (
              SELECT 1 FROM identity_accounts
              WHERE id = identity AND provider_subject <> subject AND provider_subject NOT LIKE 'local:%'
            ) THEN
              RAISE EXCEPTION 'provider subject mismatch' USING ERRCODE = '42501';
            END IF;
            UPDATE identity_accounts
            SET provider_subject = subject,
                mfa_required = CASE WHEN require_mfa THEN true ELSE mfa_required END
            WHERE id = identity;
          END IF;

          INSERT INTO identity_sessions (
            id, identity_id, organization_id, token_hash, csrf_hash, assurance, device_label,
            idle_expires_at, absolute_expires_at, reauthenticated_at, idle_window,
            provider_session_id, refresh_ciphertext
          ) VALUES (
            session_id, identity, org, token_hash, csrf_hash, assurance, device,
            idle_until, absolute_until, now(), make_interval(secs => idle_seconds),
            provider_session, refresh_ciphertext
          );
          RETURN session_id;
        END;
        $$;
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

"""Let the invited person accept a grant without opening every grant in the organization.

payment.pay is not a reason to see or rewrite another tenancy's invitation.
"""
from alembic import op

revision = "0060_phase17_grant_accept"
down_revision = "0059_phase17_grant_owner"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION perchpoint.payment_actor_email()
        RETURNS text
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
          SELECT email FROM accounts WHERE id = perchpoint.current_actor()
        $$;
        GRANT EXECUTE ON FUNCTION perchpoint.payment_actor_email() TO perchpoint_runtime, perchpoint_definer;

        DROP POLICY payer_grants_scope ON payer_grants;
        CREATE POLICY payer_grants_scope ON payer_grants
          USING (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.charge')
              OR payer_account_id = perchpoint.current_actor()
              OR grantor_account_id = perchpoint.current_actor()
              OR (
                state = 'invited'
                AND lower(email) = lower(perchpoint.payment_actor_email())
              )
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.charge')
              OR (
                grantor_account_id = perchpoint.current_actor()
                AND perchpoint.payment_actor_owns_tenancy(tenancy_code)
              )
              OR (
                payer_account_id = perchpoint.current_actor()
                AND state = 'active'
                AND lower(email) = lower(perchpoint.payment_actor_email())
              )
            )
          );
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

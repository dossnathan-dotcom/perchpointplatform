"""Break the payer-grant policy cycle without widening tenancy authority.

The grant insert checked payment obligations, and the obligation policy checks
payer grants. A security-definer ownership function keeps that check off the
row-security path.
"""
from alembic import op

revision = "0059_phase17_grant_owner"
down_revision = "0058_phase17_tenancy_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION perchpoint.payment_actor_owns_tenancy(tenancy text)
        RETURNS boolean
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
          SELECT EXISTS (
            SELECT 1 FROM payment_obligations obligation
            WHERE obligation.organization_id = perchpoint.current_org()
              AND obligation.tenancy_code = tenancy
              AND obligation.primary_account_id = perchpoint.current_actor()
          )
        $$;
        GRANT EXECUTE ON FUNCTION perchpoint.payment_actor_owns_tenancy(text) TO perchpoint_runtime, perchpoint_definer;

        DROP POLICY payer_grants_scope ON payer_grants;
        CREATE POLICY payer_grants_scope ON payer_grants
          USING (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.charge')
              OR perchpoint.has_capability('payment.pay')
              OR payer_account_id = perchpoint.current_actor()
              OR grantor_account_id = perchpoint.current_actor()
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.charge')
              OR (
                grantor_account_id = perchpoint.current_actor()
                AND perchpoint.payment_actor_owns_tenancy(tenancy_code)
              )
            )
          );
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

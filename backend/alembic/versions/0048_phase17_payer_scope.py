"""Let an active additional payer see obligation totals without another household's records."""
from alembic import op

revision = "0048_phase17_payer_scope"
down_revision = "0047_phase17_autopay_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP POLICY payment_orders_scope ON payment_orders;
        CREATE POLICY payment_orders_scope ON payment_orders
          USING (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.charge')
              OR perchpoint.has_capability('payment.refund')
              OR perchpoint.has_capability('payment.exception')
              OR payer_account_id = perchpoint.current_actor()
              OR EXISTS (
                SELECT 1 FROM payer_grants grant_row
                WHERE grant_row.organization_id = payment_orders.organization_id
                  AND grant_row.tenancy_code = payment_orders.tenancy_code
                  AND grant_row.payer_account_id = perchpoint.current_actor()
                  AND grant_row.state = 'active'
              )
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.pay')
              OR perchpoint.has_capability('payment.charge')
            )
          );
        DROP POLICY collection_reservations_scope ON collection_reservations;
        CREATE POLICY collection_reservations_scope ON collection_reservations
          USING (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.pay')
              OR perchpoint.has_capability('payment.charge')
              OR perchpoint.has_capability('payment.refund')
              OR EXISTS (
                SELECT 1 FROM payment_obligations obligation
                JOIN payer_grants grant_row
                  ON grant_row.organization_id = obligation.organization_id
                 AND grant_row.tenancy_code = obligation.tenancy_code
                WHERE obligation.id = collection_reservations.obligation_id
                  AND grant_row.payer_account_id = perchpoint.current_actor()
                  AND grant_row.state = 'active'
              )
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.pay')
              OR perchpoint.has_capability('payment.charge')
            )
          );
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

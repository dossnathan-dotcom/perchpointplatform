"""Allow charge publishers to record the local merchant and receipt."""
from alembic import op

revision = "0046_phase17_payment_scope"
down_revision = "0045_phase17_payments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP POLICY payment_merchant_configs_scope ON payment_merchant_configs;
        CREATE POLICY payment_merchant_configs_scope ON payment_merchant_configs
          USING (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('payment.configure') OR perchpoint.has_capability('payment.charge')))
          WITH CHECK (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('payment.configure') OR perchpoint.has_capability('payment.charge')));
        DROP POLICY payment_receipts_scope ON payment_receipts;
        CREATE POLICY payment_receipts_scope ON payment_receipts
          USING (organization_id = perchpoint.current_org() AND (
            payer_account_id = perchpoint.current_actor()
            OR perchpoint.has_capability('payment.charge')
            OR perchpoint.has_capability('payment.refund')
          ))
          WITH CHECK (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge')));
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

"""Let an authorized charge publisher enroll a synthetic autopay instrument."""
from alembic import op

revision = "0047_phase17_autopay_scope"
down_revision = "0046_phase17_payment_scope"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP POLICY payment_instruments_scope ON payment_instruments;
        CREATE POLICY payment_instruments_scope ON payment_instruments
          USING (
            organization_id = perchpoint.current_org() AND (
              payer_account_id = perchpoint.current_actor()
              OR perchpoint.has_capability('payment.charge')
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org()
            AND payer_account_id = perchpoint.current_actor()
            AND (perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge'))
          );
        DROP POLICY autopay_enrollments_scope ON autopay_enrollments;
        CREATE POLICY autopay_enrollments_scope ON autopay_enrollments
          USING (organization_id = perchpoint.current_org() AND (
            payer_account_id = perchpoint.current_actor() OR perchpoint.has_capability('payment.charge')
          ))
          WITH CHECK (
            organization_id = perchpoint.current_org()
            AND payer_account_id = perchpoint.current_actor()
            AND (perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge'))
          );
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

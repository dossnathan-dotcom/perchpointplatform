"""Keep refund and autopay facts inside the tenancy the actor actually belongs to.

payment.read is not authority to list another household's refunds, and payment.pay
is not authority to invite a payer or enroll autopay for an unrelated tenancy.
"""
from alembic import op

revision = "0058_phase17_tenancy_scope"
down_revision = "0057_phase17_autopay_due"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        DROP POLICY refund_cases_scope ON refund_cases;
        CREATE POLICY refund_cases_scope ON refund_cases
          USING (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.refund')
              OR perchpoint.has_capability('payment.exception')
              OR perchpoint.has_capability('payment.charge')
              OR EXISTS (
                SELECT 1 FROM payment_obligations obligation
                WHERE obligation.organization_id = refund_cases.organization_id
                  AND obligation.tenancy_code = refund_cases.tenancy_code
                  AND obligation.primary_account_id = perchpoint.current_actor()
              )
              OR EXISTS (
                SELECT 1 FROM payer_grants grant_row
                WHERE grant_row.organization_id = refund_cases.organization_id
                  AND grant_row.tenancy_code = refund_cases.tenancy_code
                  AND grant_row.payer_account_id = perchpoint.current_actor()
                  AND grant_row.state = 'active'
              )
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.refund') OR perchpoint.has_capability('payment.exception')
            )
          );

        DROP POLICY processor_disputes_scope ON processor_disputes;
        CREATE POLICY processor_disputes_scope ON processor_disputes
          USING (
            organization_id = perchpoint.current_org() AND (
              perchpoint.has_capability('payment.refund')
              OR perchpoint.has_capability('payment.charge')
              OR perchpoint.has_capability('payment.exception')
              OR EXISTS (
                SELECT 1 FROM payment_obligations obligation
                WHERE obligation.organization_id = processor_disputes.organization_id
                  AND obligation.tenancy_code = processor_disputes.tenancy_code
                  AND obligation.primary_account_id = perchpoint.current_actor()
              )
              OR EXISTS (
                SELECT 1 FROM payer_grants grant_row
                WHERE grant_row.organization_id = processor_disputes.organization_id
                  AND grant_row.tenancy_code = processor_disputes.tenancy_code
                  AND grant_row.payer_account_id = perchpoint.current_actor()
                  AND grant_row.state = 'active'
              )
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.refund')
          );

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
                AND EXISTS (
                  SELECT 1 FROM payment_obligations obligation
                  WHERE obligation.organization_id = payer_grants.organization_id
                    AND obligation.tenancy_code = payer_grants.tenancy_code
                    AND obligation.primary_account_id = perchpoint.current_actor()
                )
              )
            )
          );

        DROP POLICY autopay_enrollments_scope ON autopay_enrollments;
        CREATE POLICY autopay_enrollments_scope ON autopay_enrollments
          USING (
            organization_id = perchpoint.current_org() AND (
              payer_account_id = perchpoint.current_actor()
              OR perchpoint.has_capability('payment.charge')
              OR EXISTS (
                SELECT 1 FROM payment_obligations obligation
                WHERE obligation.organization_id = autopay_enrollments.organization_id
                  AND obligation.tenancy_code = autopay_enrollments.tenancy_code
                  AND obligation.primary_account_id = perchpoint.current_actor()
              )
            )
          )
          WITH CHECK (
            organization_id = perchpoint.current_org()
            AND payer_account_id = perchpoint.current_actor()
            AND (
              perchpoint.has_capability('payment.charge')
              OR EXISTS (
                SELECT 1 FROM payment_obligations obligation
                WHERE obligation.organization_id = autopay_enrollments.organization_id
                  AND obligation.tenancy_code = autopay_enrollments.tenancy_code
                  AND obligation.primary_account_id = perchpoint.current_actor()
              )
              OR EXISTS (
                SELECT 1 FROM payer_grants grant_row
                WHERE grant_row.organization_id = autopay_enrollments.organization_id
                  AND grant_row.tenancy_code = autopay_enrollments.tenancy_code
                  AND grant_row.payer_account_id = perchpoint.current_actor()
                  AND grant_row.state = 'active'
              )
            )
          );
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

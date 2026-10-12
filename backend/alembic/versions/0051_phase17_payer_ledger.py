"""Let an active additional payer post and read the granted tenancy ledger."""
from alembic import op

revision = "0051_phase17_payer_ledger"
down_revision = "0050_phase17_payer_mfa"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE POLICY resident_accounts_payer_read ON resident_accounts
          FOR SELECT
          USING (
            organization_id = perchpoint.current_org()
            AND EXISTS (
              SELECT 1 FROM payment_obligations obligation
              JOIN payer_grants grant_row
                ON grant_row.organization_id = obligation.organization_id
               AND grant_row.tenancy_code = obligation.tenancy_code
              WHERE obligation.account_reference = resident_accounts.public_reference
                AND grant_row.payer_account_id = perchpoint.current_actor()
                AND grant_row.state = 'active'
            )
          );
        CREATE POLICY journal_lines_payer_read ON journal_lines
          FOR SELECT
          USING (
            organization_id = perchpoint.current_org()
            AND EXISTS (
              SELECT 1 FROM journal_transactions posted
              JOIN payer_grants grant_row
                ON grant_row.organization_id = posted.organization_id
               AND grant_row.tenancy_code = posted.tenancy_code
              WHERE posted.id = journal_lines.transaction_id
                AND posted.organization_id = journal_lines.organization_id
                AND grant_row.payer_account_id = perchpoint.current_actor()
                AND grant_row.state = 'active'
            )
          );
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

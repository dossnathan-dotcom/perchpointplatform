"""Store the authenticated provider payload for later normalization."""
from alembic import op

revision = "0052_phase17_event_payload"
down_revision = "0051_phase17_payer_ledger"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE provider_events
          ADD COLUMN payload jsonb NOT NULL DEFAULT '{}'::jsonb;
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 provider payload is forward-only")

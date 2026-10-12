"""Let the security-definer capability check call the session helpers.

A fresh head granted perchpoint.current_actor() only to perchpoint_runtime.
perchpoint.has_capability() runs as perchpoint_definer, so runtime payment
policies failed at startup. The long-lived demo already had this grant.
"""
from alembic import op

revision = "0053_phase17_definer_execute"
down_revision = "0052_phase17_event_payload"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        GRANT EXECUTE ON FUNCTION perchpoint.current_actor(), perchpoint.current_org()
          TO perchpoint_definer;
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 definer execute grants are forward-only")

"""Record attributable access-review decisions and completion state."""
from pathlib import Path

from alembic import op

revision = "0023_phase6_review_decisions"
down_revision = "0022_phase6_contact_subject"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0023_phase6_access_review_decisions.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        ALTER TABLE access_review_items
          DROP COLUMN IF EXISTS change_payload,
          DROP COLUMN IF EXISTS decided_at,
          DROP COLUMN IF EXISTS decision,
          DROP COLUMN IF EXISTS reviewer_id;
        ALTER TABLE access_review_campaigns
          DROP COLUMN IF EXISTS completed_at,
          DROP COLUMN IF EXISTS owner_account_id;
        """
    )

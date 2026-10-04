"""Add bounded delegation scope, decision types, and append-only usage."""
from pathlib import Path

from alembic import op

revision = "0024_phase6_delegation_usage"
down_revision = "0023_phase6_review_decisions"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0024_phase6_delegation_usage.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS delegation_usage;
        ALTER TABLE delegations
          DROP COLUMN IF EXISTS decision_types;
        """
    )

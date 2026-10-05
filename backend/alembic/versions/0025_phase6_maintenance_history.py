"""Preserve attributed maintenance recommendations and decisions separately."""
from pathlib import Path

from alembic import op

revision = "0025_phase6_maintenance_history"
down_revision = "0024_phase6_delegation_usage"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0025_phase6_maintenance_history.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP TABLE IF EXISTS maintenance_case_events, maintenance_cases")

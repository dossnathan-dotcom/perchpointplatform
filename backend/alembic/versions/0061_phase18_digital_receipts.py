"""Digital receipt evidence and housing-assistance schedules. Forward-only. No live money movement."""
from pathlib import Path

from alembic import op

revision = "0061_phase18_digital_receipts"
down_revision = "0060_phase17_grant_accept"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0061_phase18_digital_receipts.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 18 assistance facts are forward-only")

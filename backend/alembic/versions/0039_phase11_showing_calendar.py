"""Phase 11 showing scheduling and calendar synchronization. Forward-only."""
from pathlib import Path

from alembic import op

revision = "0039_phase11_showing"
down_revision = "0038_phase10_inquiry"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0039_phase11_showing_calendar.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 11 showing calendar is forward-only")

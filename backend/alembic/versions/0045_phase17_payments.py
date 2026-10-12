"""Phase 17 synthetic payment orchestration. Forward-only. No live money movement."""
from pathlib import Path

from alembic import op

revision = "0045_phase17_payments"
down_revision = "0044_phase16_ledger"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0045_phase17_payments.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 17 payment facts are forward-only")

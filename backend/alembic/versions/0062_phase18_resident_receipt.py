"""Resident-funded digital receipts share the payment reservation path. Forward-only."""
from pathlib import Path

from alembic import op

revision = "0062_phase18_resident_receipt"
down_revision = "0061_phase18_digital_receipts"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0062_phase18_resident_receipt.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 18 assistance facts are forward-only")

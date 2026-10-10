"""Phase 16 operational resident ledger. Forward-only."""
from pathlib import Path

from alembic import op

revision = "0044_phase16_ledger"
down_revision = "0043_phase15_resident_portal"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0044_phase16_ledger.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 16 resident ledger facts are forward-only")

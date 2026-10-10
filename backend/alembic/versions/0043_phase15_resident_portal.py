"""Phase 15 resident portal membership, documents, and governed requests. Forward-only."""
from pathlib import Path

from alembic import op

revision = "0043_phase15_resident_portal"
down_revision = "0042_phase14_lease"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0043_phase15_resident_portal.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 15 resident portal facts are forward-only")

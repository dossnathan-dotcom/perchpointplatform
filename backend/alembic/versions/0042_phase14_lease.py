"""Phase 14 lease preparation, fake signature, deposit obligation, and activation. Forward-only."""
from pathlib import Path

from alembic import op

revision = "0042_phase14_lease"
down_revision = "0041_phase13_screening"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0042_phase14_lease.sql"


def upgrade() -> None:
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade() -> None:
    raise RuntimeError("Phase 14 lease activation is forward-only")

"""Add the Phase 7 public analytics intake function."""
from pathlib import Path

from alembic import op

revision = "0033_phase7_public_controls"
down_revision = "0032_phase7_public_content"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0033_phase7_public_controls.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("0033 public controls require a reviewed forward migration")

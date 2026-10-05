"""Add Phase 7 scheduled publication jobs."""
from pathlib import Path

from alembic import op

revision = "0034_phase7_publication_jobs"
down_revision = "0033_phase7_public_controls"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0034_phase7_publication_jobs.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("0034 publication jobs require a reviewed forward migration")

"""Reconcile technician property visibility with active assignments."""
from pathlib import Path

from alembic import op

revision = "0035_phase7_property_visibility"
down_revision = "0034_phase7_publication_jobs"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0035_phase7_property_visibility.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("0035 property visibility requires a reviewed forward migration")

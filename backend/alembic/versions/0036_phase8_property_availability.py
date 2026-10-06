"""Canonical property pricing, media, holds, and publication snapshots."""
from pathlib import Path

from alembic import op

revision = "0036_phase8_availability"
down_revision = "0035_phase7_property_visibility"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0036_phase8_property_availability.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("0036 property availability requires a reviewed forward migration")

"""Derived discovery projections for HawkVision-owned surfaces."""
from pathlib import Path

from alembic import op

revision = "0037_phase9_discovery"
down_revision = "0036_phase8_availability"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0037_phase9_listing_discovery.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("0037 listing discovery requires a reviewed forward migration")

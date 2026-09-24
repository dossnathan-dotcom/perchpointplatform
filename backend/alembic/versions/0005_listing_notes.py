"""Listing versions and inquiry notes. Applied after 0004."""
from pathlib import Path

from alembic import op

revision = "0005_listing_notes"
down_revision = "0004_inbox_order"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(Path(__file__).resolve().parents[1].joinpath("sql", "0005_listing_notes.sql").read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP TABLE IF EXISTS inquiry_notes")
    op.execute("ALTER TABLE listings DROP COLUMN IF EXISTS version")

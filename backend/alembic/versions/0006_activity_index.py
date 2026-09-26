"""Index activity timelines. The 250,000-row measurement sorted the table."""
from pathlib import Path

from alembic import op

revision = "0006_activity_index"
down_revision = "0005_listing_notes"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(Path(__file__).resolve().parents[1].joinpath("sql", "0006_activity_index.sql").read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP INDEX IF EXISTS activity_resource_time")

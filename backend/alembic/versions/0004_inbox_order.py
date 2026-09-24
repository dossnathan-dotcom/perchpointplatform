"""Compare inbox order within one provider account, not inquiry versions."""
from pathlib import Path

from alembic import op

revision = "0004_inbox_order"
down_revision = "0003_inbox_names"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("SET ROLE perchpoint_definer")
    op.execute(Path(__file__).resolve().parents[1].joinpath("sql", "0004_inbox_order.sql").read_text(encoding="utf-8"))
    op.execute("RESET ROLE")


def downgrade():
    op.execute("SELECT 1")

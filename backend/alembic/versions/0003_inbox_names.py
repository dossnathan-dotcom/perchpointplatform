"""Replace accept_inbox so conflict targets are not ambiguous."""
from pathlib import Path

from alembic import op

revision = "0003_inbox_names"
down_revision = "0002_phase2_commands"
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).resolve().parents[1].joinpath("sql", "0002_phase2_commands.sql").read_text(encoding="utf-8")
    start = sql.index("CREATE OR REPLACE FUNCTION perchpoint.accept_inbox")
    op.execute("SET ROLE perchpoint_definer")
    op.execute("DROP FUNCTION IF EXISTS perchpoint.accept_inbox(uuid, text, text, text, text, jsonb, integer);\n" + sql[start:])
    op.execute("RESET ROLE")


def downgrade():
    op.execute("SELECT 1")

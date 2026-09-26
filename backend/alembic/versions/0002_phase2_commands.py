"""Inbox acceptance and outbox claim payload. No revision before 0001 exists."""
from pathlib import Path

from alembic import op

revision = "0002_phase2_commands"
down_revision = "0001_phase2_reference"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0002_phase2_commands.sql"


def upgrade():
    script = SQL.read_text(encoding="utf-8")
    op.execute("GRANT USAGE, CREATE ON SCHEMA perchpoint TO perchpoint_definer")
    op.execute("DROP FUNCTION IF EXISTS perchpoint.claim_outbox(text)")
    op.execute("SET ROLE perchpoint_definer")
    body = script.split("DROP FUNCTION IF EXISTS perchpoint.claim_outbox(text);", 1)[1]
    op.execute(body)
    op.execute("RESET ROLE")


def downgrade():
    op.execute("DROP FUNCTION IF EXISTS perchpoint.accept_inbox(uuid, text, text, text, text, jsonb, integer)")
    op.execute("DROP FUNCTION IF EXISTS perchpoint.claim_outbox(text)")

"""Phase 6 invitation lookup that runs before a tenant session exists."""
from pathlib import Path

from alembic import op

revision = "0013_phase6_bootstrap"
down_revision = "0012_phase6_identity"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0013_phase6_bootstrap.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP FUNCTION IF EXISTS perchpoint.claim_invitation(text)")

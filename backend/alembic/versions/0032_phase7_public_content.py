"""Add Phase 7 public content, publication, and intake tables."""
from pathlib import Path

from alembic import op

revision = "0032_phase7_public_content"
down_revision = "0031_phase6_authz_remediation"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0032_phase7_public_content.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("0032 public content requires a reviewed forward migration")

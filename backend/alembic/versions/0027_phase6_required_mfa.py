"""Require provider MFA for existing and newly mapped workforce identities."""
from pathlib import Path

from alembic import op

revision = "0027_phase6_required_mfa"
down_revision = "0026_phase6_vendor_workers"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0027_phase6_required_mfa.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    pass

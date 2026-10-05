"""Make selected membership, capabilities, scopes, and assignments authoritative."""
from pathlib import Path

from alembic import op

revision = "0031_phase6_authz_remediation"
down_revision = "0030_phase6_recovery_provider"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0031_phase6_authorization_remediation.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    raise RuntimeError("0031 contains security policy changes and requires a reviewed forward migration")

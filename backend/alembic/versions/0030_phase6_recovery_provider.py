"""Expose only the provider subject needed for an authorized ready recovery."""
from pathlib import Path

from alembic import op

revision = "0030_phase6_recovery_provider"
down_revision = "0029_phase6_invite_reauth"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0030_phase6_recovery_provider.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute("DROP FUNCTION IF EXISTS perchpoint.recovery_provider_subject(uuid, uuid, uuid)")

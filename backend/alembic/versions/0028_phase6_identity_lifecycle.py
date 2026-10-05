"""Add attributable suspension, offboarding, and nonresurrecting restoration."""
from pathlib import Path

from alembic import op

revision = "0028_phase6_identity_lifecycle"
down_revision = "0027_phase6_required_mfa"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0028_phase6_identity_lifecycle.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.set_identity_lifecycle(uuid, uuid, uuid, text, text);
        DROP TABLE IF EXISTS identity_lifecycle_events;
        """
    )

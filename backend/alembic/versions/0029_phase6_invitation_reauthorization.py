"""Recheck inviter authority and deny privileged role invitations at acceptance."""
from pathlib import Path

from alembic import op

revision = "0029_phase6_invite_reauth"
down_revision = "0028_phase6_identity_lifecycle"
branch_labels = None
depends_on = None

SOURCE = Path(__file__).resolve().parents[1] / "sql" / "0020_phase6_invitation_activation.sql"


def upgrade():
    sql = SOURCE.read_text(encoding="utf-8")
    op.execute(sql[sql.index("CREATE OR REPLACE FUNCTION") :])


def downgrade():
    pass

"""Phase 6 identity, session, delegation, and access-governance tables."""
from pathlib import Path

from alembic import op

revision = "0012_phase6_identity"
down_revision = "0011_phase5_hold_guard"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0012_phase6_identity.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP TABLE IF EXISTS security_events, service_principals, access_requests, delegations,
          identity_invitations, identity_recovery_codes, identity_factors, identity_sessions, identity_accounts;
        """
    )

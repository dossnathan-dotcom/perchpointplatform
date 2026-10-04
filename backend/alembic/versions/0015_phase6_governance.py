"""Complete Phase 6 governance metadata and recovery-code consumption."""
from pathlib import Path

from alembic import op

revision = "0015_phase6_governance"
down_revision = "0014_phase6_provider"
branch_labels = None
depends_on = None

SQL = Path(__file__).resolve().parents[1] / "sql" / "0015_phase6_governance.sql"


def upgrade():
    op.execute(SQL.read_text(encoding="utf-8"))


def downgrade():
    op.execute(
        """
        DROP FUNCTION IF EXISTS perchpoint.consume_recovery_code(uuid, uuid);
        DROP FUNCTION IF EXISTS perchpoint.recovery_code_material(uuid);
        DROP TABLE IF EXISTS membership_role_assignments, delegation_events, identity_contact_history;
        ALTER TABLE security_events
          DROP COLUMN IF EXISTS details, DROP COLUMN IF EXISTS reason_code,
          DROP COLUMN IF EXISTS resource_id, DROP COLUMN IF EXISTS resource_type,
          DROP COLUMN IF EXISTS actor_account_id, DROP COLUMN IF EXISTS request_id;
        ALTER TABLE identity_sessions
          DROP COLUMN IF EXISTS refresh_reuse_detected_at, DROP COLUMN IF EXISTS refresh_generation,
          DROP COLUMN IF EXISTS refresh_family_id;
        ALTER TABLE service_principals
          DROP COLUMN IF EXISTS revoked_at, DROP COLUMN IF EXISTS last_used_at,
          DROP COLUMN IF EXISTS capabilities, DROP COLUMN IF EXISTS audience;
        ALTER TABLE access_requests
          DROP COLUMN IF EXISTS decided_at, DROP COLUMN IF EXISTS requested_until,
          DROP COLUMN IF EXISTS scope_resource_id, DROP COLUMN IF EXISTS scope_type,
          DROP COLUMN IF EXISTS purpose;
        ALTER TABLE identity_invitations
          DROP COLUMN IF EXISTS replaced_by, DROP COLUMN IF EXISTS accepted_identity_id,
          DROP COLUMN IF EXISTS approval_status, DROP COLUMN IF EXISTS scope_payload,
          DROP COLUMN IF EXISTS relationship_id, DROP COLUMN IF EXISTS relationship_type;
        """
    )

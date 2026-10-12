"""Let the runtime worker list due autopay without a superuser session.

The worker still posts provider events through the application admin
connection. This function only returns the due enrollment identity.
"""
from alembic import op

revision = "0054_phase17_worker_claim"
down_revision = "0053_phase17_definer_execute"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE FUNCTION perchpoint.due_autopay_claims(day_number integer)
        RETURNS TABLE (organization_id uuid, tenancy_code text, payer_account_id uuid)
        LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
          SELECT enrollment.organization_id, enrollment.tenancy_code, enrollment.payer_account_id
          FROM autopay_enrollments enrollment
          WHERE enrollment.state = 'active' AND enrollment.day_of_month = day_number
        $$;
        ALTER FUNCTION perchpoint.due_autopay_claims(integer) OWNER TO perchpoint_definer;
        REVOKE ALL ON FUNCTION perchpoint.due_autopay_claims(integer) FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION perchpoint.due_autopay_claims(integer) TO perchpoint_runtime;
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 worker claim is forward-only")

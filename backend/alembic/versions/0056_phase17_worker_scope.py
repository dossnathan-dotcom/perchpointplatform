"""Quarantine provider events whose organization is not a real tenant.

A signed callback can name an organization that has no row. Creating a
worker principal for that id fails the foreign key and blocks every other
received event. Those deliveries are quarantined before scopes are listed.
"""
from alembic import op

revision = "0056_phase17_worker_scope"
down_revision = "0055_phase17_worker_inbox"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE FUNCTION perchpoint.payment_inbox_scopes()
        RETURNS TABLE (organization_id uuid, principal_id uuid)
        LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
        DECLARE
          target uuid;
        BEGIN
          UPDATE provider_events event
          SET state = 'quarantined'
          WHERE event.state = 'received'
            AND NOT EXISTS (
              SELECT 1 FROM organizations organization WHERE organization.id = event.organization_id
            );
          FOR target IN
            SELECT DISTINCT event.organization_id
            FROM provider_events event
            WHERE event.state = 'received'
          LOOP
            INSERT INTO service_principals (organization_id, id, name, status, capabilities)
            SELECT target, gen_random_uuid(), 'phase17-payment-worker', 'active',
              ARRAY['payment.pay', 'payment.charge', 'payment.configure', 'payment.refund']::text[]
            WHERE NOT EXISTS (
              SELECT 1 FROM service_principals principal
              WHERE principal.organization_id = target
                AND principal.name = 'phase17-payment-worker'
                AND principal.status = 'active'
                AND principal.revoked_at IS NULL
            );
            organization_id := target;
            principal_id := (
              SELECT principal.id FROM service_principals principal
              WHERE principal.organization_id = target
                AND principal.name = 'phase17-payment-worker'
                AND principal.status = 'active'
                AND principal.revoked_at IS NULL
              ORDER BY principal.id
              LIMIT 1
            );
            RETURN NEXT;
          END LOOP;
        END $$;
        ALTER FUNCTION perchpoint.payment_inbox_scopes() OWNER TO perchpoint_definer;
        REVOKE ALL ON FUNCTION perchpoint.payment_inbox_scopes() FROM PUBLIC;
        GRANT EXECUTE ON FUNCTION perchpoint.payment_inbox_scopes() TO perchpoint_runtime;
        """
    )


def downgrade() -> None:
    raise RuntimeError("Phase 17 worker scope is forward-only")

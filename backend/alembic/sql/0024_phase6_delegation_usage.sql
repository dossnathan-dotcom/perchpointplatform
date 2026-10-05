ALTER TABLE delegations
  ADD COLUMN decision_types text[] NOT NULL DEFAULT ARRAY[]::text[];

UPDATE delegations
SET decision_types = ARRAY[decision_type]
WHERE decision_type IS NOT NULL;

CREATE TABLE delegation_usage (
  organization_id uuid NOT NULL REFERENCES organizations(id),
  id uuid NOT NULL,
  delegation_id uuid NOT NULL,
  actor_id uuid NOT NULL,
  capability text NOT NULL,
  resource_type text NOT NULL,
  resource_id uuid,
  decision_type text NOT NULL,
  amount_minor integer CHECK (amount_minor IS NULL OR amount_minor >= 0),
  related_transaction_key text,
  request_id uuid NOT NULL,
  occurred_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, delegation_id)
    REFERENCES delegations(organization_id, id)
);

ALTER TABLE delegation_usage ENABLE ROW LEVEL SECURITY;
ALTER TABLE delegation_usage FORCE ROW LEVEL SECURITY;

CREATE POLICY delegation_usage_scope ON delegation_usage
  USING (
    organization_id = perchpoint.current_org()
    AND perchpoint.actor_in_org(organization_id)
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND actor_id = perchpoint.current_actor()
    AND perchpoint.actor_in_org(organization_id)
  );

GRANT SELECT, INSERT ON delegation_usage TO perchpoint_runtime, perchpoint_definer;
REVOKE UPDATE, DELETE ON delegation_usage FROM perchpoint_runtime;

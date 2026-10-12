-- Phase 17 payment orchestration. Local synthetic collection only.
-- Live merchant activity, real instrument data, and money movement stay closed.

ALTER TABLE journal_transactions ADD COLUMN tenancy_code text;

DO $$
DECLARE constraint_name text;
BEGIN
  SELECT conname INTO constraint_name FROM pg_constraint
  WHERE conrelid = 'journal_transactions'::regclass AND contype = 'c'
    AND pg_get_constraintdef(oid) LIKE '%settlement%';
  IF constraint_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE journal_transactions DROP CONSTRAINT %I', constraint_name);
  END IF;
  SELECT conname INTO constraint_name FROM pg_constraint
  WHERE conrelid = 'journal_lines'::regclass AND contype = 'c'
    AND pg_get_constraintdef(oid) LIKE '%prepayment%';
  IF constraint_name IS NOT NULL THEN
    EXECUTE format('ALTER TABLE journal_lines DROP CONSTRAINT %I', constraint_name);
  END IF;
END $$;

ALTER TABLE journal_transactions ADD CONSTRAINT journal_transactions_kind_check
  CHECK (kind IN ('charge', 'subsidy', 'deposit', 'settlement', 'reversal', 'waiver', 'refund', 'return', 'processor_expense'));
ALTER TABLE journal_lines ADD CONSTRAINT journal_lines_category_check
  CHECK (category IN ('receivable', 'income', 'subsidy', 'deposit', 'unapplied', 'prepayment', 'liability', 'processor_expense'));

CREATE TABLE payment_merchant_configs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  entity_code text NOT NULL,
  environment text NOT NULL CHECK (environment = 'local_fake'),
  provider text NOT NULL CHECK (provider = 'stripe'),
  live_enabled boolean NOT NULL,
  resident_surcharge boolean NOT NULL,
  zone_name text NOT NULL,
  real_values_activated boolean NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, entity_code),
  CHECK (live_enabled = false),
  CHECK (resident_surcharge = false),
  CHECK (real_values_activated = false)
);

CREATE TABLE payment_obligations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  tenancy_code text NOT NULL,
  account_reference text,
  primary_account_id uuid,
  category text NOT NULL CHECK (category IN ('rent', 'fee', 'deposit', 'preactivation')),
  description text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  due_on date,
  state text NOT NULL CHECK (state IN ('published', 'held')),
  currency_code text NOT NULL CHECK (currency_code = 'USD'),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE payer_grants (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  tenancy_code text NOT NULL,
  payer_account_id uuid,
  grantor_account_id uuid NOT NULL,
  email text NOT NULL,
  state text NOT NULL CHECK (state IN ('invited', 'active', 'revoked', 'expired')),
  token_hash text,
  expires_at timestamptz,
  accepted_at timestamptz,
  revoked_at timestamptz,
  PRIMARY KEY (organization_id, id)
);

CREATE UNIQUE INDEX payer_grants_one_active
  ON payer_grants (organization_id, tenancy_code) WHERE state = 'active';

CREATE TABLE payment_instruments (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  payer_account_id uuid NOT NULL,
  provider_reference text NOT NULL,
  method text NOT NULL CHECK (method IN ('card', 'ach')),
  display_label text NOT NULL,
  environment text NOT NULL CHECK (environment = 'local_fake'),
  state text NOT NULL CHECK (state IN ('synthetic', 'revoked')),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, provider_reference)
);

CREATE TABLE payment_orders (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  obligation_id uuid NOT NULL,
  tenancy_code text NOT NULL,
  payer_account_id uuid NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  fee_minor integer NOT NULL CHECK (fee_minor = 0),
  method text NOT NULL CHECK (method IN ('card', 'ach')),
  state text NOT NULL CHECK (state IN ('processing', 'succeeded', 'failed', 'canceled', 'unknown')),
  environment text NOT NULL CHECK (environment = 'local_fake'),
  idempotency_key text NOT NULL,
  ledger_reference text,
  ledger_status text NOT NULL CHECK (ledger_status IN ('posted', 'not_linked', 'pending')),
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, idempotency_key),
  FOREIGN KEY (organization_id, obligation_id) REFERENCES payment_obligations (organization_id, id)
);

CREATE TABLE payment_attempts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  order_id uuid NOT NULL,
  provider_reference text,
  state text NOT NULL CHECK (state IN ('processing', 'succeeded', 'failed', 'unknown')),
  scenario text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, order_id) REFERENCES payment_orders (organization_id, id)
);

CREATE TABLE collection_reservations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  obligation_id uuid NOT NULL,
  order_id uuid NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  state text NOT NULL CHECK (state IN ('active', 'consumed', 'released')),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, order_id),
  FOREIGN KEY (organization_id, obligation_id) REFERENCES payment_obligations (organization_id, id)
);

CREATE UNIQUE INDEX collection_one_active
  ON collection_reservations (organization_id, obligation_id) WHERE state = 'active';

CREATE TABLE autopay_enrollments (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  tenancy_code text NOT NULL,
  payer_account_id uuid NOT NULL,
  instrument_id uuid NOT NULL,
  cap_minor integer NOT NULL CHECK (cap_minor > 0),
  day_of_month integer NOT NULL CHECK (day_of_month BETWEEN 1 AND 28),
  zone_name text NOT NULL,
  state text NOT NULL CHECK (state IN ('active', 'paused', 'canceled')),
  policy_version text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, instrument_id) REFERENCES payment_instruments (organization_id, id)
);

CREATE UNIQUE INDEX autopay_one_active
  ON autopay_enrollments (organization_id, tenancy_code) WHERE state = 'active';

CREATE TABLE autopay_occurrences (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  enrollment_id uuid NOT NULL,
  period_code text NOT NULL,
  state text NOT NULL CHECK (state IN ('scheduled', 'skipped', 'action_required', 'collected', 'canceled')),
  amount_minor integer,
  reason text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, enrollment_id, period_code),
  FOREIGN KEY (organization_id, enrollment_id) REFERENCES autopay_enrollments (organization_id, id)
);

CREATE TABLE provider_events (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  provider_event_id text NOT NULL,
  effect_key text NOT NULL,
  state text NOT NULL CHECK (state IN ('received', 'applied', 'quarantined')),
  payload_kind text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, provider_event_id)
);

CREATE TABLE tenancy_refund_budgets (
  organization_id uuid NOT NULL,
  tenancy_code text NOT NULL,
  snapshot_minor integer NOT NULL CHECK (snapshot_minor > 0),
  current_minor integer NOT NULL CHECK (current_minor > 0),
  period_start date NOT NULL,
  zone_name text NOT NULL,
  PRIMARY KEY (organization_id, tenancy_code)
);

CREATE TABLE refund_cases (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  tenancy_code text NOT NULL,
  order_id uuid NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  reason_category text NOT NULL,
  description text NOT NULL,
  resident_explanation text NOT NULL,
  state text NOT NULL CHECK (state IN (
    'reserved', 'owner_decision_required', 'owner_approved', 'succeeded', 'failed', 'unknown', 'rejected'
  )),
  exception_reference text,
  ledger_reference text,
  idempotency_key text NOT NULL,
  authorized_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, idempotency_key),
  FOREIGN KEY (organization_id, order_id) REFERENCES payment_orders (organization_id, id)
);

CREATE TABLE payment_receipts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  order_id uuid NOT NULL,
  payer_account_id uuid NOT NULL,
  tenancy_code text NOT NULL,
  body text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, order_id),
  FOREIGN KEY (organization_id, order_id) REFERENCES payment_orders (organization_id, id),
  CHECK (position('SYNTHETIC PAYMENT RECEIPT' in body) > 0)
);

CREATE TABLE payment_notices (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  tenancy_code text NOT NULL,
  recipient_account_id uuid,
  kind text NOT NULL,
  state text NOT NULL CHECK (state = 'synthetic_local'),
  body text NOT NULL,
  PRIMARY KEY (organization_id, id)
);

CREATE TABLE processor_disputes (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  public_reference text NOT NULL UNIQUE,
  order_id uuid NOT NULL,
  tenancy_code text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  reason_code text NOT NULL,
  state text NOT NULL CHECK (state IN ('open', 'evidence_needed', 'won', 'lost')),
  deadline_on date,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, order_id) REFERENCES payment_orders (organization_id, id)
);

CREATE TABLE payment_commands (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

ALTER TABLE payment_merchant_configs ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_merchant_configs FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_obligations ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_obligations FORCE ROW LEVEL SECURITY;
ALTER TABLE payer_grants ENABLE ROW LEVEL SECURITY;
ALTER TABLE payer_grants FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_instruments ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_instruments FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_orders ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_orders FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_attempts ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_attempts FORCE ROW LEVEL SECURITY;
ALTER TABLE collection_reservations ENABLE ROW LEVEL SECURITY;
ALTER TABLE collection_reservations FORCE ROW LEVEL SECURITY;
ALTER TABLE autopay_enrollments ENABLE ROW LEVEL SECURITY;
ALTER TABLE autopay_enrollments FORCE ROW LEVEL SECURITY;
ALTER TABLE autopay_occurrences ENABLE ROW LEVEL SECURITY;
ALTER TABLE autopay_occurrences FORCE ROW LEVEL SECURITY;
ALTER TABLE provider_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE provider_events FORCE ROW LEVEL SECURITY;
ALTER TABLE tenancy_refund_budgets ENABLE ROW LEVEL SECURITY;
ALTER TABLE tenancy_refund_budgets FORCE ROW LEVEL SECURITY;
ALTER TABLE refund_cases ENABLE ROW LEVEL SECURITY;
ALTER TABLE refund_cases FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_receipts ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_receipts FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_notices ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_notices FORCE ROW LEVEL SECURITY;
ALTER TABLE processor_disputes ENABLE ROW LEVEL SECURITY;
ALTER TABLE processor_disputes FORCE ROW LEVEL SECURITY;
ALTER TABLE payment_commands ENABLE ROW LEVEL SECURITY;
ALTER TABLE payment_commands FORCE ROW LEVEL SECURITY;

CREATE POLICY payment_merchant_configs_scope ON payment_merchant_configs
  USING (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('payment.configure') OR perchpoint.has_capability('payment.charge')))
  WITH CHECK (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('payment.configure') OR perchpoint.has_capability('payment.charge')));

CREATE POLICY payment_obligations_scope ON payment_obligations
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('payment.charge')
      OR perchpoint.has_capability('payment.refund')
      OR perchpoint.has_capability('payment.exception')
      OR primary_account_id = perchpoint.current_actor()
      OR EXISTS (
        SELECT 1 FROM payer_grants grant_row
        WHERE grant_row.organization_id = payment_obligations.organization_id
          AND grant_row.tenancy_code = payment_obligations.tenancy_code
          AND grant_row.payer_account_id = perchpoint.current_actor()
          AND grant_row.state = 'active'
      )
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('payment.charge')
      OR primary_account_id = perchpoint.current_actor()
    )
  );

CREATE POLICY payer_grants_scope ON payer_grants
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('payment.charge')
      OR perchpoint.has_capability('payment.pay')
      OR payer_account_id = perchpoint.current_actor()
      OR grantor_account_id = perchpoint.current_actor()
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('payment.pay')
      OR perchpoint.has_capability('payment.charge')
    )
  );

CREATE POLICY payment_instruments_scope ON payment_instruments
  USING (
    organization_id = perchpoint.current_org() AND (
      payer_account_id = perchpoint.current_actor()
      OR perchpoint.has_capability('payment.charge')
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND payer_account_id = perchpoint.current_actor()
    AND perchpoint.has_capability('payment.pay')
  );

CREATE POLICY payment_orders_scope ON payment_orders
  USING (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('payment.charge')
      OR perchpoint.has_capability('payment.refund')
      OR perchpoint.has_capability('payment.exception')
      OR payer_account_id = perchpoint.current_actor()
    )
  )
  WITH CHECK (
    organization_id = perchpoint.current_org() AND (
      perchpoint.has_capability('payment.pay')
      OR perchpoint.has_capability('payment.charge')
    )
  );

CREATE POLICY payment_attempts_scope ON payment_attempts
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge') OR perchpoint.has_capability('payment.refund')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge')
  ));

CREATE POLICY collection_reservations_scope ON collection_reservations
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge') OR perchpoint.has_capability('payment.refund')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge')
  ));

CREATE POLICY autopay_enrollments_scope ON autopay_enrollments
  USING (organization_id = perchpoint.current_org() AND (
    payer_account_id = perchpoint.current_actor() OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.pay') AND payer_account_id = perchpoint.current_actor());

CREATE POLICY autopay_occurrences_scope ON autopay_occurrences
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge')
  ));

CREATE POLICY provider_events_scope ON provider_events
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.configure'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.configure'));

CREATE POLICY tenancy_refund_budgets_scope ON tenancy_refund_budgets
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.refund') OR perchpoint.has_capability('payment.exception') OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.refund') OR perchpoint.has_capability('payment.charge') OR perchpoint.has_capability('payment.exception')
  ));

CREATE POLICY refund_cases_scope ON refund_cases
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.refund')
    OR perchpoint.has_capability('payment.exception')
    OR perchpoint.has_capability('payment.read')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.refund') OR perchpoint.has_capability('payment.exception')
  ));

CREATE POLICY payment_receipts_scope ON payment_receipts
  USING (organization_id = perchpoint.current_org() AND (
    payer_account_id = perchpoint.current_actor()
    OR perchpoint.has_capability('payment.charge')
    OR perchpoint.has_capability('payment.refund')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge')));

CREATE POLICY payment_notices_scope ON payment_notices
  USING (organization_id = perchpoint.current_org() AND (
    recipient_account_id = perchpoint.current_actor() OR perchpoint.has_capability('payment.charge')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay') OR perchpoint.has_capability('payment.charge') OR perchpoint.has_capability('payment.refund')
  ));

CREATE POLICY processor_disputes_scope ON processor_disputes
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.refund') OR perchpoint.has_capability('payment.charge') OR perchpoint.has_capability('payment.read')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.refund'));

CREATE POLICY payment_commands_scope ON payment_commands
  USING (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay')
    OR perchpoint.has_capability('payment.charge')
    OR perchpoint.has_capability('payment.refund')
    OR perchpoint.has_capability('payment.exception')
  ))
  WITH CHECK (organization_id = perchpoint.current_org() AND (
    perchpoint.has_capability('payment.pay')
    OR perchpoint.has_capability('payment.charge')
    OR perchpoint.has_capability('payment.refund')
    OR perchpoint.has_capability('payment.exception')
  ));

CREATE POLICY resident_accounts_payment_read ON resident_accounts
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND EXISTS (
      SELECT 1 FROM payment_obligations obligation
      WHERE obligation.organization_id = resident_accounts.organization_id
        AND obligation.account_reference = resident_accounts.public_reference
        AND obligation.primary_account_id = perchpoint.current_actor()
    )
  );

CREATE POLICY accounting_periods_payment_read ON accounting_periods
  FOR SELECT
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('payment.pay'));

CREATE POLICY journal_lines_payment_read ON journal_lines
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND EXISTS (
      SELECT 1 FROM journal_transactions posted
      WHERE posted.id = journal_lines.transaction_id
        AND posted.organization_id = journal_lines.organization_id
        AND posted.tenancy_code IS NOT NULL
        AND EXISTS (
          SELECT 1 FROM payment_obligations obligation
          WHERE obligation.organization_id = posted.organization_id
            AND obligation.tenancy_code = posted.tenancy_code
            AND obligation.primary_account_id = perchpoint.current_actor()
        )
    )
  );

CREATE POLICY ledger_allocations_payment_insert ON ledger_allocations
  FOR INSERT
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('payment.pay')
  );

CREATE POLICY journal_transactions_payment_read ON journal_transactions
  FOR SELECT
  USING (
    organization_id = perchpoint.current_org()
    AND tenancy_code IS NOT NULL
    AND EXISTS (
      SELECT 1 FROM payment_obligations obligation
      WHERE obligation.organization_id = journal_transactions.organization_id
        AND obligation.tenancy_code = journal_transactions.tenancy_code
        AND (
          obligation.primary_account_id = perchpoint.current_actor()
          OR EXISTS (
            SELECT 1 FROM payer_grants grant_row
            WHERE grant_row.organization_id = obligation.organization_id
              AND grant_row.tenancy_code = obligation.tenancy_code
              AND grant_row.payer_account_id = perchpoint.current_actor()
              AND grant_row.state = 'active'
          )
        )
    )
  );

CREATE POLICY journal_transactions_payment_insert ON journal_transactions
  FOR INSERT
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND money_moved = false
    AND kind IN ('settlement', 'refund', 'return', 'processor_expense')
    AND tenancy_code IS NOT NULL
    AND perchpoint.has_capability('payment.pay')
  );

CREATE POLICY journal_lines_payment_insert ON journal_lines
  FOR INSERT
  WITH CHECK (
    organization_id = perchpoint.current_org()
    AND perchpoint.has_capability('payment.pay')
    AND EXISTS (
      SELECT 1 FROM journal_transactions posted
      WHERE posted.id = transaction_id
        AND posted.organization_id = journal_lines.organization_id
        AND posted.money_moved = false
        AND posted.kind IN ('settlement', 'refund', 'return', 'processor_expense')
    )
  );

GRANT SELECT, INSERT, UPDATE ON payment_merchant_configs, payment_obligations, payer_grants,
  payment_instruments, payment_orders, payment_attempts, collection_reservations,
  autopay_enrollments, autopay_occurrences, provider_events, tenancy_refund_budgets,
  refund_cases, payment_receipts, payment_notices, processor_disputes, payment_commands
  TO perchpoint_runtime, perchpoint_definer;

SET LOCAL ROLE perchpoint_definer;

INSERT INTO capabilities (code, family, description) VALUES
  ('payment.read', 'payments', 'Read payment status in an authorized scope'),
  ('payment.pay', 'payments', 'Start a synthetic payment for an authorized tenancy'),
  ('payment.charge', 'payments', 'Publish a payable obligation'),
  ('payment.refund', 'payments', 'Approve an ordinary refund within the tenancy cap'),
  ('payment.exception', 'payments', 'Record an exact owner refund exception'),
  ('payment.configure', 'payments', 'Read local payment integration health')
ON CONFLICT (code) DO UPDATE SET family = EXCLUDED.family, description = EXCLUDED.description;

INSERT INTO role_bundles (id, name, version)
SELECT gen_random_uuid(), 'additional_payer', 1
WHERE NOT EXISTS (SELECT 1 FROM role_bundles WHERE name = 'additional_payer');

WITH grants(role_name, capability) AS (
  VALUES
    ('resident', 'payment.read'),
    ('resident', 'payment.pay'),
    ('additional_payer', 'identity.profile.read'),
    ('additional_payer', 'session.read'),
    ('additional_payer', 'session.revoke'),
    ('additional_payer', 'payment.read'),
    ('additional_payer', 'payment.pay'),
    ('operations_manager', 'payment.read'),
    ('operations_manager', 'payment.charge'),
    ('operations_manager', 'payment.refund'),
    ('owner', 'payment.read'),
    ('owner', 'payment.charge'),
    ('owner', 'payment.refund'),
    ('owner', 'payment.exception'),
    ('platform_admin', 'payment.read'),
    ('platform_admin', 'payment.charge'),
    ('platform_admin', 'payment.configure')
)
INSERT INTO role_bundle_capabilities (bundle_id, capability)
SELECT bundle.id, grants.capability
FROM grants JOIN role_bundles bundle ON bundle.name = grants.role_name
ON CONFLICT DO NOTHING;

RESET ROLE;

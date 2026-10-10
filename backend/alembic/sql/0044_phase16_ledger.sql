-- Phase 16 posts an operational resident subledger. It does not move money,
-- call a payment processor, or claim to be a formal general ledger.

CREATE TABLE resident_accounts (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  membership_id uuid NOT NULL,
  public_reference text NOT NULL,
  period_code text NOT NULL,
  entity_code text NOT NULL,
  state text NOT NULL CHECK (state = 'open'),
  currency_code text NOT NULL CHECK (currency_code = 'USD'),
  PRIMARY KEY (organization_id, id),
  UNIQUE (public_reference),
  UNIQUE (organization_id, membership_id),
  FOREIGN KEY (organization_id, membership_id) REFERENCES portal_memberships (organization_id, id)
);

CREATE TABLE accounting_periods (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  period_code text NOT NULL,
  state text NOT NULL CHECK (state IN ('open', 'closed')),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, period_code)
);

CREATE TABLE ledger_intake_keys (
  organization_id uuid NOT NULL,
  idempotency_key text NOT NULL,
  fingerprint text NOT NULL,
  public_reference text NOT NULL,
  PRIMARY KEY (organization_id, idempotency_key)
);

CREATE TABLE journal_transactions (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  account_id uuid NOT NULL,
  period_id uuid NOT NULL,
  public_reference text NOT NULL,
  kind text NOT NULL CHECK (kind IN ('charge', 'subsidy', 'deposit', 'settlement', 'reversal', 'waiver')),
  reversal_of uuid,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  money_moved boolean NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (public_reference),
  UNIQUE (organization_id, reversal_of),
  FOREIGN KEY (organization_id, account_id) REFERENCES resident_accounts (organization_id, id),
  FOREIGN KEY (organization_id, period_id) REFERENCES accounting_periods (organization_id, id),
  CHECK (money_moved = false)
);

CREATE TABLE journal_lines (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  transaction_id uuid NOT NULL,
  side text NOT NULL CHECK (side IN ('debit', 'credit')),
  category text NOT NULL CHECK (category IN ('receivable', 'income', 'subsidy', 'deposit', 'unapplied', 'prepayment', 'liability')),
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, transaction_id) REFERENCES journal_transactions (organization_id, id)
);

CREATE TABLE charge_schedules (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  account_id uuid NOT NULL,
  occurrence_code text NOT NULL,
  amount_minor integer NOT NULL CHECK (amount_minor > 0),
  category text NOT NULL CHECK (category IN ('rent', 'fee')),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, account_id, occurrence_code),
  FOREIGN KEY (organization_id, account_id) REFERENCES resident_accounts (organization_id, id)
);

CREATE TABLE ledger_allocations (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  settlement_id uuid NOT NULL,
  amount_applied_minor integer NOT NULL CHECK (amount_applied_minor >= 0),
  amount_unapplied_minor integer NOT NULL CHECK (amount_unapplied_minor >= 0),
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, settlement_id),
  FOREIGN KEY (organization_id, settlement_id) REFERENCES journal_transactions (organization_id, id),
  CHECK (amount_applied_minor + amount_unapplied_minor > 0)
);

CREATE TABLE resident_statements (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  account_id uuid NOT NULL,
  version integer NOT NULL CHECK (version >= 1),
  content_hash text NOT NULL,
  due_minor integer NOT NULL CHECK (due_minor >= 0),
  body text NOT NULL,
  PRIMARY KEY (organization_id, id),
  UNIQUE (organization_id, account_id, version),
  FOREIGN KEY (organization_id, account_id) REFERENCES resident_accounts (organization_id, id),
  CHECK (position('SYNTHETIC OPERATIONAL STATEMENT' in body) > 0)
);

CREATE TABLE ledger_disputes (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  account_id uuid NOT NULL,
  state text NOT NULL CHECK (state = 'submitted'),
  reason_code text NOT NULL,
  PRIMARY KEY (organization_id, id),
  FOREIGN KEY (organization_id, account_id) REFERENCES resident_accounts (organization_id, id)
);

CREATE TABLE ledger_manifest_runs (
  organization_id uuid NOT NULL,
  id uuid NOT NULL,
  manifest_version integer NOT NULL CHECK (manifest_version >= 1),
  dry_run boolean NOT NULL,
  real_values_activated boolean NOT NULL,
  PRIMARY KEY (organization_id, id),
  CHECK (dry_run),
  CHECK (real_values_activated = false)
);

CREATE INDEX resident_accounts_queue ON resident_accounts (organization_id, public_reference);
CREATE INDEX journal_lines_transaction ON journal_lines (organization_id, transaction_id);
CREATE INDEX journal_transactions_account ON journal_transactions (organization_id, account_id, kind);

ALTER TABLE resident_accounts ENABLE ROW LEVEL SECURITY;
ALTER TABLE resident_accounts FORCE ROW LEVEL SECURITY;
ALTER TABLE accounting_periods ENABLE ROW LEVEL SECURITY;
ALTER TABLE accounting_periods FORCE ROW LEVEL SECURITY;
ALTER TABLE ledger_intake_keys ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_intake_keys FORCE ROW LEVEL SECURITY;
ALTER TABLE journal_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_transactions FORCE ROW LEVEL SECURITY;
ALTER TABLE journal_lines ENABLE ROW LEVEL SECURITY;
ALTER TABLE journal_lines FORCE ROW LEVEL SECURITY;
ALTER TABLE charge_schedules ENABLE ROW LEVEL SECURITY;
ALTER TABLE charge_schedules FORCE ROW LEVEL SECURITY;
ALTER TABLE ledger_allocations ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_allocations FORCE ROW LEVEL SECURITY;
ALTER TABLE resident_statements ENABLE ROW LEVEL SECURITY;
ALTER TABLE resident_statements FORCE ROW LEVEL SECURITY;
ALTER TABLE ledger_disputes ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_disputes FORCE ROW LEVEL SECURITY;
ALTER TABLE ledger_manifest_runs ENABLE ROW LEVEL SECURITY;
ALTER TABLE ledger_manifest_runs FORCE ROW LEVEL SECURITY;

CREATE POLICY resident_accounts_scope ON resident_accounts
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY accounting_periods_scope ON accounting_periods
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY ledger_intake_keys_scope ON ledger_intake_keys
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY journal_transactions_scope ON journal_transactions
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY journal_lines_scope ON journal_lines
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY charge_schedules_scope ON charge_schedules
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY ledger_allocations_scope ON ledger_allocations
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY resident_statements_scope ON resident_statements
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY ledger_disputes_scope ON ledger_disputes
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));
CREATE POLICY ledger_manifest_runs_scope ON ledger_manifest_runs
  USING (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'))
  WITH CHECK (organization_id = perchpoint.current_org() AND perchpoint.has_capability('inquiry.manage'));

GRANT SELECT, INSERT, UPDATE, DELETE ON resident_accounts, accounting_periods, ledger_intake_keys,
  charge_schedules, ledger_allocations, resident_statements, ledger_disputes, ledger_manifest_runs
  TO perchpoint_runtime, perchpoint_definer;
GRANT SELECT, INSERT ON journal_transactions, journal_lines TO perchpoint_runtime, perchpoint_definer;

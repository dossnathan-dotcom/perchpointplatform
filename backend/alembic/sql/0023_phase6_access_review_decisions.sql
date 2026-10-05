ALTER TABLE access_review_campaigns
  ADD COLUMN owner_account_id uuid,
  ADD COLUMN completed_at timestamptz;

ALTER TABLE access_review_items
  ADD COLUMN reviewer_id uuid,
  ADD COLUMN decision text CHECK (decision IN ('attest', 'revoke', 'change')),
  ADD COLUMN decided_at timestamptz,
  ADD COLUMN change_payload jsonb NOT NULL DEFAULT '{}'::jsonb;

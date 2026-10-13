-- A household can be opened by name, and a required return can record one verified completion.

ALTER TABLE assistance_determinations ADD COLUMN household_label text;

ALTER TABLE assistance_exceptions ADD COLUMN journal_reference text;
ALTER TABLE assistance_exceptions ADD COLUMN evidence_key text;

CREATE UNIQUE INDEX assistance_exceptions_evidence_once
  ON assistance_exceptions (organization_id, evidence_key)
  WHERE evidence_key IS NOT NULL;

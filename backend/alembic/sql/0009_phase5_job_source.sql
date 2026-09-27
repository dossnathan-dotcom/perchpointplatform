ALTER TABLE document_jobs ADD COLUMN source_name text NOT NULL DEFAULT 'upload.bin';
ALTER TABLE document_jobs ADD COLUMN media_type text NOT NULL DEFAULT 'application/octet-stream';
CREATE INDEX IF NOT EXISTS audit_events_org_action ON audit_events (organization_id, action);

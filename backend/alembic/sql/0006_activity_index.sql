CREATE INDEX IF NOT EXISTS activity_resource_time ON activity (organization_id, resource_id, occurred_at);

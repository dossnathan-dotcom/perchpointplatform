CREATE FUNCTION perchpoint.recovery_provider_subject(
  recovery uuid,
  actor uuid,
  org uuid
)
RETURNS text
LANGUAGE sql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
  SELECT identity.provider_subject
  FROM privileged_recoveries recovery_record
  JOIN identity_accounts identity
    ON identity.account_id = recovery_record.subject_account
  WHERE recovery_record.id = $1
    AND recovery_record.organization_id = $3
    AND recovery_record.initiator_account = $2
    AND recovery_record.not_before <= now()
    AND (
      recovery_record.approver_account IS NULL
      OR recovery_record.status = 'ready'
    )
    AND recovery_record.status IN ('waiting', 'ready')
$$;

REVOKE ALL ON FUNCTION perchpoint.recovery_provider_subject(uuid, uuid, uuid)
  FROM PUBLIC;
GRANT EXECUTE ON FUNCTION perchpoint.recovery_provider_subject(uuid, uuid, uuid)
  TO perchpoint_runtime;

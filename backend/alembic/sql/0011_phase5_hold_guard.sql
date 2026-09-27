CREATE OR REPLACE FUNCTION perchpoint.reject_held_mutation()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  target uuid;
BEGIN
  IF TG_TABLE_NAME = 'documents' THEN
    target := OLD.id;
  ELSE
    target := OLD.document_id;
  END IF;
  IF EXISTS (
    SELECT 1 FROM legal_holds
    WHERE document_id = target AND released_at IS NULL
  ) THEN
    IF TG_OP = 'DELETE' OR TG_TABLE_NAME <> 'documents' OR NEW.lifecycle IN ('disposed', 'rejected') THEN
      RAISE EXCEPTION 'legal hold blocks mutation' USING ERRCODE = '42501';
    END IF;
  END IF;
  IF TG_OP = 'DELETE' THEN
    RETURN OLD;
  END IF;
  RETURN NEW;
END;
$$;

ALTER FUNCTION perchpoint.reject_held_mutation() OWNER TO perchpoint_definer;

DROP TRIGGER IF EXISTS documents_hold_guard ON documents;
CREATE TRIGGER documents_hold_guard
  BEFORE DELETE OR UPDATE ON documents
  FOR EACH ROW EXECUTE FUNCTION perchpoint.reject_held_mutation();

DROP TRIGGER IF EXISTS document_versions_hold_guard ON document_versions;
CREATE TRIGGER document_versions_hold_guard
  BEFORE DELETE OR UPDATE ON document_versions
  FOR EACH ROW EXECUTE FUNCTION perchpoint.reject_held_mutation();

DROP TRIGGER IF EXISTS document_artifacts_hold_guard ON document_artifacts;
CREATE TRIGGER document_artifacts_hold_guard
  BEFORE DELETE OR UPDATE ON document_artifacts
  FOR EACH ROW EXECUTE FUNCTION perchpoint.reject_held_mutation();

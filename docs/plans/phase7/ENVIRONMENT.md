# Phase 7 acceptance environment

The authoritative Phase 7 database is the disposable Docker project `perchpoint-phase7-accept`. Postgres is published on `127.0.0.1:54339`, GoTrue on `127.0.0.1:9998`, Mailpit SMTP on `127.0.0.1:1125`, MinIO on `127.0.0.1:9100`, and ClamAV on `127.0.0.1:3410`. The database name is `perchpoint_phase2`. It was created empty, migrated to `0035_phase7_property_visibility`, and seeded twice.

The long-lived database at `127.0.0.1:5432` named `perchpoint_phase2` is not acceptance evidence. It still has an older `property_capability_scope` expression that requires `has_capability('property.read')` and `scope_allows`, and it contains historical properties. A technician assigned only to Example Elm Court can see other properties there. The fresh database does not. Migration `0035` reapplies assignment-aware policies for databases that upgrade. This closeout did not drop, rewrite, or migrate that long-lived database.

Runtime and worker roles on the acceptance database remain `NOSUPERUSER` and `NOBYPASSRLS`.

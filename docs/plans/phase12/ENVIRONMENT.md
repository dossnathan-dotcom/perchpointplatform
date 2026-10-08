# Phase 12 acceptance environment

Local gates used the disposable Docker project `perchpoint-phase8-accept`. Postgres is published on `127.0.0.1:54339`, GoTrue on `127.0.0.1:9998`, Mailpit on `127.0.0.1:8125`, MinIO on `127.0.0.1:9100`, and ClamAV on `127.0.0.1:3410`. The database name is `perchpoint_phase2`.

P12-R15 created a separate project, `perchpoint-phase12-cleanroom`, from empty volumes, migrated it to `0040_phase12_application`, ran bootstrap, seed, the backend suite, and then removed that project's containers and volumes. The acceptance project was stopped only while those host ports were borrowed and was started again afterward. Its volumes were not removed.

The long-lived database at `127.0.0.1:5432` is not acceptance evidence.

Runtime role on these databases is `NOSUPERUSER` and `NOBYPASSRLS`.

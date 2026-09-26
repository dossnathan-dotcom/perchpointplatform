# Local Docker

Prerequisites: Docker Desktop with the WSL 2 backend, or another Docker engine that can run `docker compose`. Native PostgreSQL on port 5432 is left alone. Compose uses host port 54329.

From the repository root:

```powershell
docker compose -p perchpoint-phase3 up --build migrate
docker compose -p perchpoint-phase3 up --build seed
docker compose -p perchpoint-phase3 up --build api worker web
```

Seed may be run twice. The second run must not duplicate Elm Court. The web container serves the production build with the Python standard library on container port 8080, published at `http://127.0.0.1:3000`, and proxies `/api` to the API container through `API_UPSTREAM`. Liveness is `http://127.0.0.1:8000/api/v2/health/live`. Readiness is `http://127.0.0.1:8000/api/v2/health/ready`. Version is `http://127.0.0.1:8000/api/v2/version`.

After the stack is healthy, the disposable checks are:

```powershell
$env:PHASE2_DEV_PASSWORD = "<the disposable Compose value>"
python scripts/phase3_clean_room.py
docker compose -p perchpoint-phase3 run --rm --no-deps --entrypoint python -v "${PWD}/scripts/phase3_rollback_drill.py:/tmp/phase3_rollback_drill.py:ro" api /tmp/phase3_rollback_drill.py
```

Measured results are in `docs/plans/phase3/ACCEPTANCE.md`. Do not print the disposable password or commit a database dump.

Stop and remove only this project:

```powershell
docker compose -p perchpoint-phase3 down --volumes
```

Do not run `docker system prune` or `docker volume prune`.

# Local Docker

Prerequisites: Docker Desktop with the WSL 2 backend, or another Docker engine that can run `docker compose`. Native PostgreSQL on port 5432 is left alone. Compose uses host port 54329.

From the repository root:

```powershell
docker compose -p perchpoint-phase3 up --build migrate
docker compose -p perchpoint-phase3 up --build seed
docker compose -p perchpoint-phase3 up --build api worker web
```

Seed may be run twice. The second run must not duplicate Elm Court. The web container serves the production build through nginx on container port 8080, published at `http://127.0.0.1:3000`, and proxies `/api` to the API container. Liveness is `http://127.0.0.1:8000/api/v2/health/live`. Readiness is `http://127.0.0.1:8000/api/v2/health/ready`. Version is `http://127.0.0.1:8000/api/v2/version`.

Stop and remove only this project:

```powershell
docker compose -p perchpoint-phase3 down --volumes
```

Do not run `docker system prune` or `docker volume prune`.

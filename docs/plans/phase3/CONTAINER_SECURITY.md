# Container security

Images are built from `deploy/Dockerfile.api` and `deploy/Dockerfile.web`. They install `backend/requirements.txt` and the frozen Yarn lockfile. They do not install `backend/requirements-legacy.txt`. Processes run as non-root. The API does not migrate on startup. Compose runs migrate, then seed, then the API, worker, and web services. Host ports bind to loopback. The Docker socket is not mounted.

CI builds both images, validates Compose, and scans them with `aquasec/trivy:0.58.1`. The scan container is the only place the Docker socket is mounted, and only inside that GitHub job. Unfixed upstream findings do not by themselves fail the job. Findings with an available fix at high or critical severity fail the job. There is no ignore file. The runtime images delete Python `ensurepip` and leftover `.whl` archives so older setuptools, wheel, jaraco.context, and msgpack copies are not present as files. The installed requirements keep the fixed releases. No image is pushed to a registry.

The Starlette 1.7.0 `TestClient` deprecation warning comes from that pinned dependency when FastAPI constructs the test client. Starlette 1.7.0 is the newest release. It does not fail tests. Owner: Nathan. Review when Starlette publishes a release that stops passing `timeout` into httpx. Do not silence the warning globally.

Local cleanup removes only the Compose project `perchpoint-phase3`. It does not prune Docker globally.

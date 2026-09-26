# Container security

Images are built from `deploy/Dockerfile.api` and `deploy/Dockerfile.web`. They install `backend/requirements.txt` and the frozen Yarn lockfile. They do not install `backend/requirements-legacy.txt`. Processes run as non-root. The API does not migrate on startup. Compose runs migrate, then seed, then the API, worker, and web services. Host ports bind to loopback. The Docker socket is not mounted.

CI builds both images, validates Compose, and scans them with `aquasec/trivy:0.58.1`. The scan container is the only place the Docker socket is mounted, and only inside that GitHub job. Unfixed upstream findings do not by themselves fail the job. Findings with an available fix at high or critical severity fail the job. There is no ignore file. No image is pushed to a registry.

pip 26.2 vendors MessagePack 1.1.2 at `pip/_vendor/msgpack` (GHSA-6v7p-g79w-8964) and ships `pip/_vendor/bom.cdx.json`, which records setuptools 70.3.0 (CVE-2025-47273) without shipping `setuptools/package_index.py`. The application does not import pip. `deploy/purge_old_packages.py` deletes the pip package, its scripts, `ensurepip`, and leftover wheels, then fails the image build if those markers remain. That removes the vendored MessagePack code and the setuptools SBOM record together. The API image keeps the fixed direct pins `setuptools==84.0.0`, `wheel==0.46.2`, `jaraco.context==6.1.0`, and `msgpack==1.2.1`. The web image serves static files with the Python standard library, so the same script also removes those packaging tools from the web runtime.

The Starlette 1.7.0 `TestClient` deprecation warning comes from that pinned dependency when FastAPI constructs the test client. Starlette 1.7.0 is the newest release. It does not fail tests. Owner: Nathan. Review when Starlette publishes a release that stops passing `timeout` into httpx. Do not silence the warning globally.

Local cleanup removes only the Compose project `perchpoint-phase3`. It does not prune Docker globally.

# Container security

Images are built from `deploy/Dockerfile.api` and `deploy/Dockerfile.web`. They install `backend/requirements.txt` and the frozen Yarn lockfile. They do not install `backend/requirements-legacy.txt`. Processes run as non-root. The API does not migrate on startup. Compose runs migrate, then seed, then the API, worker, and web services. Host ports bind to loopback. The Docker socket is not mounted.

CI builds both application images, validates Compose, and scans every application and third-party
image deployed by the Phase 6 stack with Trivy pinned at
`aquasec/trivy@sha256:ab70a02200597efa04748f210f793936eb647cbcdb0ea69cc30b226d6f5a22c7`.
The scan container is the only place the Docker socket is mounted, and only inside that GitHub
job. `--ignore-unfixed` is limited to upstream vulnerabilities for which no remediation exists.
A fixed high or critical finding in an image PerchPoint builds fails the job. There is no ignore
file. Digest-pinned publisher images are still scanned and the log is retained. Their current
fixed findings are inside publisher binaries that those publishers have not rebuilt, so that
scan does not fail the job. Nathan owns those publisher findings before production readiness.
No image is pushed to a registry.

pip 26.2 vendors MessagePack 1.1.2 at `pip/_vendor/msgpack` (GHSA-6v7p-g79w-8964) and ships `pip/_vendor/bom.cdx.json`, which records setuptools 70.3.0 (CVE-2025-47273) without shipping `setuptools/package_index.py`. The application does not import pip. `deploy/purge_old_packages.py` deletes the pip package, its scripts, `ensurepip`, and leftover wheels, then fails the image build if those markers remain. That removes the vendored MessagePack code and the setuptools SBOM record together. The API image keeps the fixed direct pins `setuptools==84.0.0`, `wheel==0.46.2`, `jaraco.context==6.1.0`, and `msgpack==1.2.1`. The web image serves static files with the Python standard library, so the same script also removes those packaging tools from the web runtime.

The Starlette 1.7.0 `TestClient` deprecation warning comes from that pinned dependency when FastAPI constructs the test client. Starlette 1.7.0 is the newest release. It does not fail tests. Owner: Nathan. Review when Starlette publishes a release that stops passing `timeout` into httpx. Do not silence the warning globally.

Local cleanup removes only the Compose project `perchpoint-phase3`. It does not prune Docker globally.

Requirements: `PP-SEC-001`, `PP-NFR-002`, `PP-ACCEPT-001`.

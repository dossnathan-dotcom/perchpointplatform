"""Portable test bootstrap for local, CI, and Emergent environments."""
from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient
from dotenv import load_dotenv


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Isolated FastAPI tests construct the application but never perform a Mongo operation.
# Keep explicit environment values authoritative while supplying safe local test defaults.
os.environ.setdefault("MONGO_URL", "mongodb://127.0.0.1:27017")
os.environ.setdefault("DB_NAME", "perchpoint_phase0_test")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")
os.environ.setdefault("PHASE0_ENABLED", "true")

load_dotenv(REPOSITORY_ROOT / "frontend/.env")


class _MemoryCollection:
    def __init__(self) -> None:
        self.documents: list[dict] = []

    async def insert_one(self, document: dict) -> None:
        self.documents.append(document.copy())


class _MemoryDatabase:
    def __init__(self) -> None:
        self.inquiries = _MemoryCollection()
        self.maintenance_requests = _MemoryCollection()


@pytest.fixture(scope="session")
def phase0_base_url() -> str:
    """Use an explicit live endpoint in CI; otherwise exercise the app in process."""
    return os.environ.get("REACT_APP_BACKEND_URL", "").rstrip("/")


@pytest.fixture(scope="session")
def phase0_http_client(phase0_base_url):
    if phase0_base_url:
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        yield session
        session.close()
        return

    import server

    server.db = _MemoryDatabase()
    with TestClient(server.app) as client:
        yield client

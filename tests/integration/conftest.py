"""Shared fixtures for HTTP integration tests against a real Postgres database."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.main import build_app

REPO_ROOT = Path(__file__).resolve().parents[2]


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers",
        "integration: requires Postgres/PostGIS (RUN_INTEGRATION_TESTS=1)",
    )


@pytest.fixture(scope="session")
def integration_enabled() -> bool:
    return os.getenv("RUN_INTEGRATION_TESTS", "").strip().lower() in {
        "1",
        "true",
        "yes",
    }


@pytest.fixture(scope="session")
def integration_database_url(integration_enabled: bool) -> str:
    if not integration_enabled:
        pytest.skip("Integration tests disabled (set RUN_INTEGRATION_TESTS=1).")
    url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://postgres:postgres@localhost:5432/aditsystem",
    )
    return url


@pytest.fixture(scope="session")
def integration_env(integration_database_url: str) -> Iterator[None]:
    """Apply migrations once per session using the integration DATABASE_URL."""
    env = os.environ.copy()
    env["DATABASE_URL"] = integration_database_url
    env.setdefault("APP_ENV", "local")
    get_settings.cache_clear()
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )
    yield
    get_settings.cache_clear()


@pytest.fixture
def integration_settings(
    integration_env: None, integration_database_url: str
) -> Settings:
    get_settings.cache_clear()
    os.environ["DATABASE_URL"] = integration_database_url
    os.environ.setdefault("APP_ENV", "local")
    return get_settings()


@pytest.fixture
async def integration_client(
    integration_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    app = build_app(integration_settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

"""Shared fixtures for HTTP integration tests against a real Postgres database."""

from __future__ import annotations

import asyncio
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Generator, Iterator
from pathlib import Path

import helpers
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from aditsystem_backend.cli.seed_development import seed_development
from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.main import build_app

REPO_ROOT = Path(__file__).resolve().parents[2]


def _write_ephemeral_jwt_keys(private_key: Path, public_key: Path) -> None:
    """Create RSA PEM fixtures for integration runs (no shell/openssl subprocess)."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_key.write_bytes(
        key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
    )
    public_key.write_bytes(
        key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
    )


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
def integration_jwt_keys(integration_enabled: bool) -> None:
    if not integration_enabled:
        pytest.skip("Integration tests disabled (set RUN_INTEGRATION_TESTS=1).")
    keys_dir = REPO_ROOT / "keys"
    private_key = keys_dir / "jwt-private.pem"
    public_key = keys_dir / "jwt-public.pem"
    if private_key.is_file() and public_key.is_file():
        return
    keys_dir.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            "openssl",
            "genpkey",
            "-algorithm",
            "RSA",
            "-pkeyopt",
            "rsa_keygen_bits:2048",
            "-out",
            str(private_key),
        ],
        check=True,
    )
    subprocess.run(
        ["openssl", "rsa", "-pubout", "-in", str(private_key), "-out", str(public_key)],
        check=True,
    )
    _write_ephemeral_jwt_keys(private_key, public_key)


@pytest.fixture(scope="session")
def integration_env(
    integration_database_url: str, integration_jwt_keys: None
) -> Iterator[None]:
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


@pytest.fixture(scope="session")
async def integration_engine(
    integration_database_url: str,
) -> AsyncIterator[AsyncEngine]:
    engine = create_async_engine(integration_database_url)
    helpers.bind_engine(engine)
    yield engine
    helpers.bind_engine(None)
    await engine.dispose()
async def integration_auth_engine(
    integration_env: None, integration_database_url: str
) -> AsyncIterator[AsyncEngine]:
    """Dedicated async engine for test auth helpers (avoids per-test engine churn)."""
    engine = create_async_engine(integration_database_url)
    helpers.bind_engine(engine)
    yield engine
    helpers.bind_engine(None)
    await engine.dispose()



@pytest.fixture(scope="session")
def integration_seed(integration_env: None, integration_database_url: str) -> None:
    """Deterministic fictional hierarchy for persona API tests."""
    os.environ["DATABASE_URL"] = integration_database_url
    os.environ.setdefault("APP_ENV", "local")
    get_settings.cache_clear()
    asyncio.run(seed_development(helpers.INTEGRATION_TEST_PASSWORD))
    get_settings.cache_clear()


@pytest.fixture
def integration_settings(
    integration_seed: None,
    integration_engine: AsyncEngine,
    integration_auth_engine: AsyncEngine,
    integration_database_url: str,
) -> Generator[Settings, None, None]:
    get_settings.cache_clear()
    os.environ["DATABASE_URL"] = integration_database_url
    os.environ.setdefault("APP_ENV", "local")
    settings = get_settings()
    helpers.bind_settings(settings)
    yield settings
    helpers.bind_settings(None)
    get_settings.cache_clear()


@pytest.fixture
async def integration_client(
    integration_settings: Settings,
) -> AsyncIterator[AsyncClient]:
    app = build_app(integration_settings)
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client

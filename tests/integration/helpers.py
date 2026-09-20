"""Shared constants and helpers for HTTP integration tests."""

from __future__ import annotations

from uuid import uuid4

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.core.security import create_access_token
from aditsystem_backend.models.auth_user import AuthUser

INTEGRATION_TEST_PASSWORD = "IntegrationTest1!"
SEED_ADMIN_EMAIL = "admin@aditsystem.test"
SEED_GENERAL_EMAIL = "general@aditsystem.test"
SEED_COORDINADOR_EMAIL = "coordinador@aditsystem.test"
SEED_ENLACE_EMAIL = "enlace@aditsystem.test"

API_PREFIX = "/api/v1"

_bound_settings: Settings | None = None
_bound_engine: AsyncEngine | None = None


def bind_settings(settings: Settings | None) -> None:
    global _bound_settings
    _bound_settings = settings


def bind_engine(engine: AsyncEngine | None) -> None:
    global _bound_engine
    _bound_engine = engine


async def _load_auth_user(email: str, settings: Settings) -> AuthUser:
    engine = _bound_engine or create_async_engine(settings.database_url)
    owns_engine = _bound_engine is None
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            result = await session.execute(
                select(AuthUser)
                .options(selectinload(AuthUser.persona))
                .where(func.lower(AuthUser.email) == email.lower())
            )
            return result.scalar_one()
    finally:
        if owns_engine:
            await engine.dispose()


async def login(
    client: AsyncClient, email: str, settings: Settings | None = None
) -> str:
    """Mint JWT for a seeded account (bypasses EmailStr .test on POST /login)."""
    config = settings or _bound_settings or get_settings()
    user = await _load_auth_user(email, config)
    return create_access_token(
        subject=user.id,
        email=user.email,
        role=user.persona.rol,
        settings=config,
    )


def bearer(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def persona_id_for_email(email: str, settings: Settings | None = None) -> str:
    config = settings or _bound_settings or get_settings()
    user = await _load_auth_user(email, config)
    return str(user.persona_id)


async def create_test_geocerca(settings: Settings | None = None) -> str:
    """Insert a geocerca row (global /geocercas API is not mounted on v1 router yet)."""
    from aditsystem_backend.schemas.geocerca import GeocercaCreate
    from aditsystem_backend.services.geocerca import GeocercaService

    config = settings or _bound_settings or get_settings()
    engine = _bound_engine or create_async_engine(config.database_url)
    owns_engine = _bound_engine is None
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    offset = (int(uuid4().hex[:4], 16) % 1000) / 100_000
    base_lon, base_lat = -99.2 + offset, 19.4 + offset
    try:
        async with session_factory() as session:
            created = await GeocercaService(session).create(
                GeocercaCreate(
                    tipo="MUNICIPIO",
                    nombre="Municipio integracion",
                    codigo=f"INT-{uuid4().hex[:8]}",
                    fuente="pytest-integration",
                    geojson_geometry={
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [base_lon, base_lat],
                                [base_lon + 0.1, base_lat],
                                [base_lon + 0.1, base_lat + 0.1],
                                [base_lon, base_lat + 0.1],
                                [base_lon, base_lat],
                            ]
                        ],
                    },
                )
            )
            await session.commit()
            return str(created.id)
    finally:
        if owns_engine:
            await engine.dispose()

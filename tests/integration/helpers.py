"""Shared constants and helpers for HTTP integration tests."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import PersonRole, TipoGeocerca
from aditsystem_backend.models.persona import Persona
from aditsystem_backend.schemas.geocerca import GeocercaCreate
from aditsystem_backend.services.geocerca import GeocercaService

INTEGRATION_TEST_PASSWORD = "IntegrationTest1!"
SEED_ADMIN_EMAIL = "admin@aditsystem.test"
SEED_GENERAL_EMAIL = "general@aditsystem.test"
SEED_COORDINADOR_EMAIL = "coordinador@aditsystem.test"
SEED_ENLACE_EMAIL = "enlace@aditsystem.test"

API_PREFIX = "/api/v1"

_bound_settings: Settings | None = None
_bound_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def bind_settings(settings: Settings | None) -> None:
    global _bound_settings
    _bound_settings = settings


def bind_engine(engine: AsyncEngine | None) -> None:
    global _bound_engine, _session_factory
    _bound_engine = engine
    _session_factory = None
    if engine is not None:
        _session_factory = async_sessionmaker(engine, expire_on_commit=False)


async def _load_auth_user(email: str, settings: Settings) -> AuthUser:
    if _session_factory is None:
        raise RuntimeError("Integration auth engine is not bound.")
    async with _session_factory() as session:
        result = await session.execute(
            select(AuthUser)
            .options(selectinload(AuthUser.persona))
            .where(func.lower(AuthUser.email) == email.lower())
        )
        user = result.scalar_one()
        assert verify_password(INTEGRATION_TEST_PASSWORD, user.password_hash)
        return user


async def persona_id_for(email: str, settings: Settings | None = None) -> UUID:
    config = settings or _bound_settings or get_settings()
    user = await _load_auth_user(email, config)
    return UUID(user.persona_id)


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


async def create_direct_login_account(
    email: str,
    password: str,
    role: PersonRole,
    *,
    parent_persona_id: str | None = None,
) -> str:
    """Insert a Persona+AuthUser pair directly, bypassing endpoint validation.

    Seed accounts use the ``@aditsystem.test`` domain, which pydantic's
    ``EmailStr`` rejects as an IANA reserved/special-use TLD on real request
    bodies (see ``login()`` above, which mints JWTs directly for that reason).
    This helper lets auth tests exercise the actual ``POST /auth/login``
    endpoint with a syntactically-normal email, and also lets them construct
    role combinations (e.g. AMIGO with an ``auth_users`` row) that the admin
    API itself would never produce, to verify login/`/me` reject them anyway.
    """
    if _session_factory is None:
        raise RuntimeError("Integration auth engine is not bound.")
    async with _session_factory() as session:
        persona = Persona(
            rol=role,
            parent_persona_id=parent_persona_id,
            nombre="Integracion",
            apellido_paterno="Login",
            apellido_materno=uuid4().hex[:8],
            telefono=f"555{uuid4().int % 10_000_000:07d}",
            fecha_registro=datetime.now(UTC),
        )
        session.add(persona)
        await session.flush()
        user = AuthUser(
            persona_id=persona.id,
            email=email,
            password_hash=hash_password(password),
            is_active=True,
        )
        session.add(user)
        await session.commit()
        return str(user.id)


async def create_integration_geocerca(codigo: str) -> str:
    """Insert a geocerca row for nested persona assignment tests."""
    if _session_factory is None:
        raise RuntimeError("Integration auth engine is not bound.")
    # Slightly unique bbox so geometry hash does not collide across runs.
    bump = (hash(codigo) % 1000) / 100_000
    payload = GeocercaCreate(
        tipo=TipoGeocerca.MUNICIPIO,
        nombre="Municipio integracion",
        codigo=codigo,
        fuente="pytest-integration",
        geojson_geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [-99.2 + bump, 19.4],
                    [-99.1 + bump, 19.4],
                    [-99.1 + bump, 19.5],
                    [-99.2 + bump, 19.5],
                    [-99.2 + bump, 19.4],
                ]
            ],
        },
    )
    async with _session_factory() as session:
        created = await GeocercaService(session).create(payload)
        return created.id

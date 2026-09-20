"""Create a deterministic, fictional development hierarchy.

This command deliberately has no production mode and requires an explicit
password source. It creates four authenticable accounts plus one AMIGO with
no ``auth_users`` row, and is safe to run repeatedly on a local database.
"""

from __future__ import annotations

import asyncio
import logging
import sys
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from aditsystem_backend.cli.bootstrap_admin import BootstrapError, resolve_password
from aditsystem_backend.core.config import get_settings
from aditsystem_backend.core.security import hash_password
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.models.persona import Persona

logger = logging.getLogger(__name__)
ALLOWED_ENVIRONMENTS = frozenset({"local", "development"})


@dataclass(frozen=True)
class SeedPerson:
    email: str | None
    role: PersonRole
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    telefono: str


SEED_PEOPLE = (
    SeedPerson(
        "admin@aditsystem.test",
        PersonRole.ADMIN,
        "Ada",
        "Prueba",
        "Admin",
        "5550100001",
    ),
    SeedPerson(
        "general@aditsystem.test",
        PersonRole.COORDINADOR_GENERAL,
        "Beto",
        "Prueba",
        "General",
        "5550100002",
    ),
    SeedPerson(
        "coordinador@aditsystem.test",
        PersonRole.COORDINADOR,
        "Carla",
        "Prueba",
        "Coordinacion",
        "5550100003",
    ),
    SeedPerson(
        "enlace@aditsystem.test",
        PersonRole.ENLACE,
        "Diego",
        "Prueba",
        "Enlace",
        "5550100004",
    ),
    SeedPerson(None, PersonRole.AMIGO, "Elena", "Prueba", "Amiga", "5550100005"),
)


def _validate_runtime() -> None:
    environment = get_settings().app_env.strip().lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise BootstrapError("El seed sólo se permite con APP_ENV local o development.")


async def _find_user(session: AsyncSession, email: str) -> AuthUser | None:
    result = await session.execute(
        select(AuthUser)
        .options(selectinload(AuthUser.persona))
        .where(func.lower(AuthUser.email) == email)
    )
    return result.scalar_one_or_none()


async def _find_seed_person(
    session: AsyncSession, definition: SeedPerson
) -> Persona | None:
    result = await session.execute(
        select(Persona).where(
            Persona.rol == definition.role,
            Persona.nombre == definition.nombre,
            Persona.apellido_paterno == definition.apellido_paterno,
            Persona.apellido_materno == definition.apellido_materno,
        )
    )
    return result.scalar_one_or_none()


async def seed_development(password: str) -> None:
    """Insert the fictional hierarchy atomically, rejecting inconsistent data."""
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            people: dict[PersonRole, Persona] = {}
            for definition in SEED_PEOPLE:
                existing = (
                    await _find_user(session, definition.email)
                    if definition.email
                    else None
                )
                if existing:
                    persona = existing.persona
                    if persona is None or persona.rol is not definition.role:
                        raise BootstrapError(
                            "El email de seed ya pertenece a una cuenta incompatible."
                        )
                    people[definition.role] = persona
                    continue

                existing_persona = await _find_seed_person(session, definition)
                if existing_persona:
                    if definition.email:
                        raise BootstrapError(
                            "La persona de seed existe sin la cuenta esperada."
                        )
                    people[definition.role] = existing_persona
                    continue

                parent = {
                    PersonRole.COORDINADOR: people.get(PersonRole.COORDINADOR_GENERAL),
                    PersonRole.ENLACE: people.get(PersonRole.COORDINADOR),
                    PersonRole.AMIGO: people.get(PersonRole.ENLACE),
                }.get(definition.role)
                persona = Persona(
                    rol=definition.role,
                    parent_persona_id=parent.id if parent else None,
                    nombre=definition.nombre,
                    apellido_paterno=definition.apellido_paterno,
                    apellido_materno=definition.apellido_materno,
                    telefono=definition.telefono,
                    fecha_registro=datetime.now(UTC),
                )
                session.add(persona)
                await session.flush()
                people[definition.role] = persona
                if definition.email:
                    session.add(
                        AuthUser(
                            persona_id=persona.id,
                            email=definition.email,
                            password_hash=hash_password(password),
                            is_active=True,
                        )
                    )
            await session.commit()
    finally:
        await engine.dispose()


async def _run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        _validate_runtime()
        password = resolve_password()
        if len(password) < 8:
            raise BootstrapError(
                "La contraseña de seed debe tener al menos 8 caracteres."
            )
        await seed_development(password)
    except BootstrapError as exc:
        logger.error("Seed de development rechazado: %s", exc)
        return exc.exit_code
    except Exception:
        logger.exception("Falló el seed de development.")
        return 1
    logger.info("Seed ficticio aplicado correctamente.")
    return 0


def main_cli() -> None:
    sys.exit(asyncio.run(_run()))

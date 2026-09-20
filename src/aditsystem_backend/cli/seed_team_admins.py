"""Provision development ADMIN accounts for the core team.

Reads email addresses from ``TEAM_ADMIN_EMAILS`` (comma-separated). Never
hardcodes production identities in code. Safe to re-run on local databases.
"""

from __future__ import annotations

import asyncio
import logging
import os
import re
import sys
from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import parseaddr

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
class TeamAdminSeedResult:
    created: int
    unchanged: int


def _validate_runtime() -> None:
    environment = get_settings().app_env.strip().lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise BootstrapError(
            "Seed de admins de equipo sólo con APP_ENV local o development."
        )


def _normalize_email(raw: str) -> str:
    _, addr = parseaddr(raw.strip())
    if not addr or "@" not in addr:
        raise BootstrapError(f"Correo inválido en TEAM_ADMIN_EMAILS: {raw!r}")
    return addr.lower()


def parse_team_admin_emails(raw: str | None) -> tuple[str, ...]:
    """Parse and deduplicate team admin emails preserving order."""
    if raw is None or not raw.strip():
        raise BootstrapError(
            "TEAM_ADMIN_EMAILS es obligatorio (lista separada por comas)."
        )
    seen: set[str] = set()
    emails: list[str] = []
    for part in raw.split(","):
        part = part.strip()
        if not part:
            continue
        email = _normalize_email(part)
        if email in seen:
            continue
        seen.add(email)
        emails.append(email)
    if not emails:
        raise BootstrapError("TEAM_ADMIN_EMAILS no contiene correos válidos.")
    return tuple(emails)


def _persona_fields_for_email(email: str, index: int) -> dict[str, str]:
    local = email.split("@", 1)[0]
    token = re.sub(r"[^a-zA-Z0-9]+", " ", local).strip() or "Admin"
    parts = token.split()
    nombre = parts[0][:120].title()
    apellido_paterno = (parts[1] if len(parts) > 1 else "Equipo")[:120].title()
    apellido_materno = "Admin"[:120]
    telefono = f"55502{index:05d}"[-30:]
    return {
        "nombre": nombre,
        "apellido_paterno": apellido_paterno,
        "apellido_materno": apellido_materno,
        "telefono": telefono,
    }


async def _find_user(session: AsyncSession, email: str) -> AuthUser | None:
    result = await session.execute(
        select(AuthUser)
        .options(selectinload(AuthUser.persona))
        .where(func.lower(AuthUser.email) == email)
    )
    return result.scalar_one_or_none()


async def seed_team_admins(
    session: AsyncSession, emails: tuple[str, ...], password: str
) -> TeamAdminSeedResult:
    created = 0
    unchanged = 0
    for index, email in enumerate(emails, start=1):
        existing = await _find_user(session, email)
        if existing is not None:
            persona = existing.persona
            if (
                persona is not None
                and persona.rol is PersonRole.ADMIN
                and existing.is_active
                and persona.deleted_at is None
            ):
                unchanged += 1
                logger.info("ADMIN de equipo ya existe: %s", email)
                continue
            raise BootstrapError(
                f"El correo {email} pertenece a una cuenta incompatible."
            )

        fields = _persona_fields_for_email(email, index)
        persona = Persona(
            rol=PersonRole.ADMIN,
            parent_persona_id=None,
            fecha_registro=datetime.now(UTC),
            **fields,
        )
        session.add(persona)
        await session.flush()
        session.add(
            AuthUser(
                persona_id=persona.id,
                email=email,
                password_hash=hash_password(password),
                is_active=True,
            )
        )
        created += 1
        logger.info("ADMIN de equipo creado: %s", email)
    await session.commit()
    return TeamAdminSeedResult(created=created, unchanged=unchanged)


async def _run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        _validate_runtime()
        emails = parse_team_admin_emails(os.getenv("TEAM_ADMIN_EMAILS"))
        password = resolve_password()
        if len(password) < 8:
            raise BootstrapError(
                "La contraseña debe tener al menos 8 caracteres (BOOTSTRAP_PASSWORD)."
            )
    except BootstrapError as exc:
        logger.error("Seed de admins de equipo rechazado: %s", exc)
        return exc.exit_code

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            result = await seed_team_admins(session, emails, password)
    except BootstrapError as exc:
        logger.error("Seed de admins de equipo falló: %s", exc)
        return exc.exit_code
    except Exception:
        logger.exception("Error inesperado en seed de admins de equipo.")
        return 1
    finally:
        await engine.dispose()

    logger.info(
        "Seed de admins de equipo completado (creados=%s, sin cambios=%s).",
        result.created,
        result.unchanged,
    )
    return 0


def main_cli() -> None:
    sys.exit(asyncio.run(_run()))

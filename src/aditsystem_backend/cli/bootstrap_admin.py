"""Bootstrap the one authorised development ADMIN account.

This CLI is intentionally not an HTTP endpoint.  It creates the final
``Persona`` + ``AuthUser`` pair atomically and is allowed only in local or
development environments.  It never prints credential material.
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from datetime import UTC, datetime
from email.utils import parseaddr

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import selectinload

from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.core.security import hash_password
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.models.persona import Persona

logger = logging.getLogger(__name__)

AUTHORIZED_BOOTSTRAP_EMAIL = "eperez@ervic.pro"
ALLOWED_ENVIRONMENTS = frozenset({"local", "development"})


class BootstrapError(Exception):
    """Raised when bootstrap cannot proceed. Carries the intended exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _fetch_secret(secret_id: str) -> str:
    """Retrieve a plain-text secret value from AWS Secrets Manager."""
    try:
        import boto3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise BootstrapError(
            "boto3 is not installed. Install the 'aws' extra or set BOOTSTRAP_PASSWORD."
        ) from exc

    try:
        import botocore.exceptions  # type: ignore[import-untyped]
    except ImportError as exc:
        raise BootstrapError("botocore is not available alongside boto3.") from exc

    try:
        response = boto3.client("secretsmanager").get_secret_value(SecretId=secret_id)
    except botocore.exceptions.ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        raise BootstrapError(
            f"Secrets Manager error [{error_code}] for configured bootstrap secret."
        ) from exc

    secret = response.get("SecretString") or ""
    if not secret:
        raise BootstrapError("Configured bootstrap secret returned an empty value.")
    return secret


def resolve_password() -> str:
    """Resolve the password without exposing it outside this process."""
    secret_id = os.getenv("BOOTSTRAP_PASSWORD_SECRET_ID", "").strip()
    if secret_id:
        return _fetch_secret(secret_id)

    env_password = os.getenv("BOOTSTRAP_PASSWORD", "").strip()
    if env_password:
        return env_password

    raise BootstrapError(
        "No password source configured. Set BOOTSTRAP_PASSWORD_SECRET_ID or BOOTSTRAP_PASSWORD."
    )


def _validate_email(email: str) -> str:
    _, addr = parseaddr(email)
    if not addr or "@" not in addr:
        raise BootstrapError(f"Invalid bootstrap email: {email!r}")
    return addr.lower()


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise BootstrapError("Password must be at least 8 characters.")


def _validate_runtime(*, settings: Settings, email: str) -> None:
    environment = settings.app_env.strip().lower()
    if environment not in ALLOWED_ENVIRONMENTS:
        raise BootstrapError(
            "Bootstrap is allowed only when APP_ENV is local or development."
        )
    if email != AUTHORIZED_BOOTSTRAP_EMAIL:
        raise BootstrapError(
            "BOOTSTRAP_EMAIL is not authorised for this controlled bootstrap."
        )


def _persona_fields_from_environment() -> dict[str, str]:
    """Return non-secret required Persona fields with safe development defaults."""
    return {
        "nombre": os.getenv("BOOTSTRAP_NOMBRE", "Administrador").strip()
        or "Administrador",
        "apellido_paterno": os.getenv(
            "BOOTSTRAP_APELLIDO_PATERNO", "Development"
        ).strip()
        or "Development",
        "apellido_materno": os.getenv("BOOTSTRAP_APELLIDO_MATERNO", "Admin").strip()
        or "Admin",
        "telefono": os.getenv("BOOTSTRAP_TELEFONO", "0000000000").strip()
        or "0000000000",
    }


async def bootstrap_admin(*, email: str, password: str, session: AsyncSession) -> None:
    """Create the authorised ADMIN Persona/AuthUser pair, idempotently.

    An existing active ADMIN account is preserved. Any other existing account
    using the email is a conflict and is left untouched. AMIGO is never an
    acceptable existing account and is never created here.
    """
    result = await session.execute(
        select(AuthUser)
        .options(selectinload(AuthUser.persona))
        .where(func.lower(AuthUser.email) == email)
    )
    existing = result.scalar_one_or_none()

    if existing is not None:
        persona = existing.persona
        if (
            persona is not None
            and persona.rol is PersonRole.ADMIN
            and existing.is_active
            and persona.deleted_at is None
        ):
            logger.info("Authorised ADMIN already exists; no changes made.")
            return
        raise BootstrapError(
            "An incompatible existing account uses the bootstrap email."
        )

    persona = Persona(
        rol=PersonRole.ADMIN,
        parent_persona_id=None,
        fecha_registro=datetime.now(UTC),
        **_persona_fields_from_environment(),
    )
    auth_user = AuthUser(
        persona=persona,
        email=email,
        password_hash=hash_password(password),
        is_active=True,
    )
    session.add(auth_user)
    await session.commit()
    logger.info("Authorised development ADMIN created successfully.")


async def _run() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    settings = get_settings()
    try:
        email_raw = os.getenv("BOOTSTRAP_EMAIL", "").strip()
        if not email_raw:
            raise BootstrapError("BOOTSTRAP_EMAIL is required.")
        email = _validate_email(email_raw)
        _validate_runtime(settings=settings, email=email)
        password = resolve_password()
        _validate_password(password)
    except BootstrapError as exc:
        logger.error("Bootstrap configuration error: %s", exc)
        return exc.exit_code

    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_factory() as session:
            await bootstrap_admin(email=email, password=password, session=session)
        return 0
    except BootstrapError as exc:
        logger.error("Bootstrap failed: %s", exc)
        return exc.exit_code
    except Exception:
        logger.exception("Unexpected error during bootstrap.")
        return 1
    finally:
        await engine.dispose()


def main_cli() -> None:
    """Entry point for the ``aditsystem-bootstrap-admin`` command."""
    sys.exit(asyncio.run(_run()))

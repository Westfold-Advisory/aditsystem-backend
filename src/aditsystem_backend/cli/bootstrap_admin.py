"""Bootstrap CLI: provision the first ADMIN account.

Password resolution order:
  1. AWS Secrets Manager — if BOOTSTRAP_PASSWORD_SECRET_ID is set.
  2. BOOTSTRAP_PASSWORD env var — local / CI dev only.
  3. BootstrapError — no silent fallback.

Idempotency contract:
  User exists and is ADMIN    → exit 0 (already provisioned, no changes).
  User exists, different role → exit 1 (explicit conflict, no changes).
  User not found              → create ADMIN, exit 0.

This module never logs or prints the password, its hash, or any token.
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys
from email.utils import parseaddr

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from aditsystem_backend.core.config import get_settings
from aditsystem_backend.core.security import hash_password
from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.models.user import User

logger = logging.getLogger(__name__)


class BootstrapError(Exception):
    """Raised when bootstrap cannot proceed. Carries the intended exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.exit_code = exit_code


# ---------------------------------------------------------------------------
# Password resolution
# ---------------------------------------------------------------------------


def _fetch_secret(secret_id: str) -> str:
    """Retrieve a plain-text secret value from AWS Secrets Manager."""
    try:
        import boto3  # type: ignore[import-untyped]
    except ImportError as exc:
        raise BootstrapError(
            "boto3 is not installed. "
            "Install the 'aws' optional extra (pip install aditsystem-backend[aws]) "
            "or set BOOTSTRAP_PASSWORD instead of BOOTSTRAP_PASSWORD_SECRET_ID."
        ) from exc

    try:
        import botocore.exceptions  # type: ignore[import-untyped]
    except ImportError as exc:
        raise BootstrapError("botocore is not available alongside boto3.") from exc

    client = boto3.client("secretsmanager")
    try:
        response = client.get_secret_value(SecretId=secret_id)
    except botocore.exceptions.ClientError as exc:
        error_code = exc.response["Error"]["Code"]
        raise BootstrapError(
            f"Secrets Manager error [{error_code}] for secret '{secret_id}'."
        ) from exc

    secret = response.get("SecretString") or ""
    if not secret:
        raise BootstrapError(f"Secret '{secret_id}' returned an empty value.")
    return secret


def resolve_password() -> str:
    """Resolve the bootstrap password. Never returns an empty string."""
    secret_id = os.getenv("BOOTSTRAP_PASSWORD_SECRET_ID", "").strip()
    if secret_id:
        return _fetch_secret(secret_id)

    env_password = os.getenv("BOOTSTRAP_PASSWORD", "").strip()
    if env_password:
        return env_password

    raise BootstrapError(
        "No password source configured. "
        "Set BOOTSTRAP_PASSWORD_SECRET_ID (AWS Secrets Manager, recommended for SSM) "
        "or BOOTSTRAP_PASSWORD (dev/local only)."
    )


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


def _validate_email(email: str) -> str:
    """Validate and normalize the email address. Returns lowercase canonical form."""
    _, addr = parseaddr(email)
    if not addr or "@" not in addr:
        raise BootstrapError(f"Invalid email address: {email!r}")
    return addr.lower()


def _validate_password(password: str) -> None:
    if len(password) < 8:
        raise BootstrapError("Password must be at least 8 characters.")


# ---------------------------------------------------------------------------
# Core bootstrap logic (testable, session-injected)
# ---------------------------------------------------------------------------


async def bootstrap_admin(
    *,
    email: str,
    full_name: str,
    password: str,
    session: AsyncSession,
) -> None:
    """Idempotently create the ADMIN user.

    Already ADMIN       → returns normally.
    Exists, other role  → raises BootstrapError(exit_code=1).
    Not found           → creates user and commits.

    The password argument is consumed only to produce a bcrypt hash and is
    never written to any log or returned in any form.
    """
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()

    if existing is not None:
        if existing.role == UserRole.ADMIN:
            logger.info("User %r is already ADMIN — no changes made.", email)
            return
        raise BootstrapError(
            f"User {email!r} already exists with role={existing.role.value!r}. "
            "Refusing to reassign role via bootstrap.",
            exit_code=1,
        )

    user = User(
        email=email,
        full_name=full_name,
        password_hash=hash_password(password),
        role=UserRole.ADMIN,
    )
    session.add(user)
    await session.commit()
    logger.info("ADMIN user %r created successfully.", email)


# ---------------------------------------------------------------------------
# CLI entry points
# ---------------------------------------------------------------------------


async def _run() -> int:
    """Execute bootstrap. Returns the intended process exit code."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    try:
        email_raw = os.getenv("BOOTSTRAP_EMAIL", "").strip()
        if not email_raw:
            raise BootstrapError("BOOTSTRAP_EMAIL is required.")
        email = _validate_email(email_raw)
        full_name = os.getenv("BOOTSTRAP_NAME", "Administrador").strip() or "Administrador"
        password = resolve_password()
        _validate_password(password)
    except BootstrapError as exc:
        logger.error("Bootstrap configuration error: %s", exc)
        return exc.exit_code

    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    session_factory = async_sessionmaker(engine, expire_on_commit=False)

    try:
        async with session_factory() as session:
            await bootstrap_admin(
                email=email,
                full_name=full_name,
                password=password,
                session=session,
            )
        return 0
    except BootstrapError as exc:
        logger.error("Bootstrap failed: %s", exc)
        return exc.exit_code
    except Exception as exc:
        logger.exception("Unexpected error during bootstrap.")
        return 1
    finally:
        await engine.dispose()


def main_cli() -> None:
    """Entry point for the `aditsystem-bootstrap-admin` CLI command."""
    sys.exit(asyncio.run(_run()))

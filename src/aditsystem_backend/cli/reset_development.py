"""Guarded, development-only PostgreSQL schema reset for the EC2 SSM runbook."""

import asyncio
import os
import sys

from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.ext.asyncio import create_async_engine

from aditsystem_backend.core.config import Settings, get_settings


class ResetError(Exception):
    """Raised when a destructive reset request fails its safety checks."""


def _configured_database_host(database_url: str) -> str:
    try:
        host = make_url(database_url).host
    except Exception as exc:
        raise ResetError("DATABASE_URL is not a valid SQLAlchemy URL.") from exc
    if not host:
        raise ResetError("DATABASE_URL must contain a database host.")
    return host.lower()


def validate_reset_request(
    *, settings: Settings,
    confirmation: str,
    expected_host: str,
    change_id: str,
) -> str:
    """Return the validated RDS hostname, or reject before opening a connection."""
    if settings.app_env.strip().lower() != "development":
        raise ResetError("Reset is allowed only when APP_ENV is exactly development.")
    if confirmation != "RESET_DEVELOPMENT_DATA":
        raise ResetError("The explicit reset confirmation is missing or invalid.")
    if not change_id.strip():
        raise ResetError("RESET_CHANGE_ID is required for an auditable reset.")

    database_host = _configured_database_host(settings.database_url)
    expected = expected_host.strip().lower()
    if not expected or database_host != expected:
        raise ResetError("RESET_DATABASE_HOST must exactly match DATABASE_URL host.")
    if not database_host.endswith(".rds.amazonaws.com") or "prod" in database_host:
        raise ResetError("DATABASE_URL host is not an allowed development RDS endpoint.")
    return database_host


async def reset_schema(*, database_url: str) -> None:
    """Drop and recreate only PostgreSQL's public schema in one transaction."""
    engine = create_async_engine(database_url, pool_pre_ping=False)
    try:
        async with engine.begin() as connection:
            await connection.execute(text("DROP SCHEMA public CASCADE"))
            await connection.execute(text("CREATE SCHEMA public"))
    finally:
        await engine.dispose()


async def _run() -> int:
    settings = get_settings()
    database_host = validate_reset_request(
        settings=settings,
        confirmation=os.getenv("RESET_CONFIRMATION", ""),
        expected_host=os.getenv("RESET_DATABASE_HOST", ""),
        change_id=os.getenv("RESET_CHANGE_ID", ""),
    )
    await reset_schema(database_url=settings.database_url)
    print(f"Development schema reset completed for approved RDS host: {database_host}")
    return 0


def main_cli() -> None:
    try:
        sys.exit(asyncio.run(_run()))
    except ResetError as exc:
        print(f"Development reset rejected: {exc}", file=sys.stderr)
        sys.exit(2)


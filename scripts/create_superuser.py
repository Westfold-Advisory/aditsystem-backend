#!/usr/bin/env python3
"""Bootstrap script to create the first ADMIN user.

Usage:
    python scripts/create_superuser.py

Reads credentials from environment variables or prompts interactively.
Required env vars (or set .env):
  DATABASE_URL  — PostgreSQL async URL
  BOOTSTRAP_EMAIL    — admin email
  BOOTSTRAP_PASSWORD — admin password (>=8 chars)
  BOOTSTRAP_NAME     — full name (optional, defaults to "Administrador")
"""

import asyncio
import os
import sys
from getpass import getpass

# Ensure src is on the path when run from the repo root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from aditsystem_backend.core.config import get_settings
from aditsystem_backend.core.security import hash_password
from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.models.user import User


async def main() -> None:
    settings = get_settings()

    email = os.getenv("BOOTSTRAP_EMAIL") or input("Admin email: ").strip()
    password = os.getenv("BOOTSTRAP_PASSWORD") or getpass("Admin password: ")
    full_name = os.getenv("BOOTSTRAP_NAME") or input("Full name [Administrador]: ").strip() or "Administrador"

    if len(password) < 8:
        print("Error: password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    engine = create_async_engine(settings.database_url)
    async_session = async_sessionmaker(engine, expire_on_commit=False)

    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == email))
        existing = result.scalar_one_or_none()
        if existing:
            print(f"User {email!r} already exists (role={existing.role}).")
            await engine.dispose()
            return

        user = User(
            email=email,
            full_name=full_name,
            password_hash=hash_password(password),
            role=UserRole.ADMIN,
        )
        session.add(user)
        await session.commit()
        print(f"Admin user {email!r} created successfully.")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())

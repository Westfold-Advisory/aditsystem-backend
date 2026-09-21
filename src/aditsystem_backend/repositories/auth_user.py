from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from aditsystem_backend.models.auth_user import AuthUser


class AuthUserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_email(self, email: str) -> AuthUser | None:
        result = await self.session.execute(
            select(AuthUser)
            .options(selectinload(AuthUser.persona))
            .where(func.lower(AuthUser.email) == email.lower())
        )
        return result.scalar_one_or_none()

    async def get_by_persona_id(self, persona_id: str) -> AuthUser | None:
        """Query directly instead of ``persona.auth_user`` — safe even when the
        persona object was just constructed in this transaction and never had
        its relationships eagerly loaded (async lazy-load is unsupported)."""
        result = await self.session.execute(select(AuthUser).where(AuthUser.persona_id == persona_id))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> AuthUser | None:
        result = await self.session.execute(
            select(AuthUser)
            .options(selectinload(AuthUser.persona))
            .where(AuthUser.id == user_id)
        )
        return result.scalar_one_or_none()

    async def create(self, user: AuthUser) -> AuthUser:
        self.session.add(user)
        await self.session.flush()
        await self.session.refresh(user)
        return user

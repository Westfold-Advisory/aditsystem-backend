from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.config import get_settings
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.models.user import User
from aditsystem_backend.repositories.user import UserRepository
from aditsystem_backend.schemas.auth import AdminUserCreate, TokenResponse, UserCreate


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = UserRepository(session)
        self.settings = get_settings()

    async def register(self, payload: UserCreate) -> User:
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise DomainError("ya existe un usuario con ese email", status_code=409)

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=UserRole.INVITADO,
            invitado_id=str(payload.invitado_id) if payload.invitado_id else None,
        )
        await self.users.create(user)
        await self.session.commit()
        return user

    async def create_user(self, payload: AdminUserCreate, actor: User) -> User:
        if actor.role != UserRole.ADMIN:
            raise DomainError(
                "solo ADMIN puede crear usuarios con roles privilegiados", status_code=403
            )
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise DomainError("ya existe un usuario con ese email", status_code=409)

        user = User(
            email=payload.email,
            full_name=payload.full_name,
            password_hash=hash_password(payload.password),
            role=payload.role,
            politico_id=str(payload.politico_id) if payload.politico_id else None,
            gestor_id=str(payload.gestor_id) if payload.gestor_id else None,
            invitado_id=str(payload.invitado_id) if payload.invitado_id else None,
        )
        await self.users.create(user)
        await self.session.commit()
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.users.get_by_email(email)
        if not user or not verify_password(password, user.password_hash):
            raise DomainError("credenciales inválidas", status_code=401)

        token = create_access_token(
            subject=user.id,
            email=user.email,
            role=user.role.value,
            expires_delta=timedelta(minutes=self.settings.jwt_access_token_expire_minutes),
        )
        return TokenResponse(
            access_token=token,
            expires_in_seconds=self.settings.jwt_access_token_expire_minutes * 60,
            user=user,
        )

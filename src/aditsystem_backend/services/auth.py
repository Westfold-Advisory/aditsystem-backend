from datetime import timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.config import get_settings
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.security import (
    create_access_token,
    hash_password,
    verify_password,
)
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import AUTHENTICABLE_PERSON_ROLES
from aditsystem_backend.repositories.auth_user import AuthUserRepository
from aditsystem_backend.repositories.persona import PersonaRepository
from aditsystem_backend.schemas.auth import AuthUserCreate, AuthUserRead, TokenResponse
from aditsystem_backend.services.persona_policy import PersonaPolicy


class AuthService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.users = AuthUserRepository(session)
        self.personas = PersonaRepository(session)
        self.settings = get_settings()

    async def create_user(self, payload: AuthUserCreate, actor: AuthUser) -> AuthUser:
        if not PersonaPolicy.is_admin(actor):
            raise DomainError("solo ADMIN puede crear cuentas", status_code=403)
        existing = await self.users.get_by_email(payload.email)
        if existing:
            raise DomainError("ya existe un usuario con ese email", status_code=409)
        persona = await self.personas.get(str(payload.persona_id))
        if not persona or persona.deleted_at is not None:
            raise DomainError("persona no encontrada", status_code=404)
        if persona.rol not in AUTHENTICABLE_PERSON_ROLES:
            raise DomainError("AMIGO no puede tener cuenta autenticable", status_code=422)
        if persona.auth_user:
            raise DomainError("la persona ya tiene una cuenta", status_code=409)
        user = AuthUser(
            email=payload.email,
            password_hash=hash_password(payload.password),
            persona_id=persona.id,
        )
        await self.users.create(user)
        await self.session.commit()
        # AuthUserRepository.create() only refreshes column attributes; the
        # `persona` relationship was never loaded on this brand-new object,
        # so callers reading `user.persona` (e.g. the response serializer)
        # would otherwise trigger an unsupported lazy load under AsyncSession.
        user.persona = persona
        return user

    async def login(self, email: str, password: str) -> TokenResponse:
        user = await self.users.get_by_email(email)
        if (
            not user
            or not user.is_active
            or user.persona.deleted_at is not None
            or user.persona.rol not in AUTHENTICABLE_PERSON_ROLES
            or not verify_password(password, user.password_hash)
        ):
            raise DomainError("credenciales inválidas", status_code=401)

        token = create_access_token(
            subject=user.id,
            email=user.email,
            role=user.persona.rol,
            expires_delta=timedelta(minutes=self.settings.jwt_access_token_expire_minutes),
        )
        return TokenResponse(
            access_token=token,
            expires_in_seconds=self.settings.jwt_access_token_expire_minutes * 60,
            user=AuthUserRead(
                id=user.id,
                email=user.email,
                persona_id=user.persona_id,
                rol=user.persona.rol,
                is_active=user.is_active,
                created_at=user.created_at,
                updated_at=user.updated_at,
            ),
        )

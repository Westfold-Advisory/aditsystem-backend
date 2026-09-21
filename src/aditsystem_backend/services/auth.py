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

    async def _assert_can_manage_credentials(self, actor: AuthUser, persona: Persona) -> None:
        policy = PersonaPolicy(self.session)
        await policy.assert_manage(actor, persona)

    async def _create_auth_user_record(self, persona: Persona, email: str, password: str) -> AuthUser:
        existing = await self.users.get_by_email(email)
        if existing:
            raise DomainError("ya existe un usuario con ese email", status_code=409)
        if persona.rol not in AUTHENTICABLE_PERSON_ROLES:
            raise DomainError("AMIGO no puede tener cuenta autenticable", status_code=422)
        if persona.auth_user:
            raise DomainError("la persona ya tiene una cuenta", status_code=409)
        user = AuthUser(
            email=email,
            password_hash=hash_password(password),
            persona_id=persona.id,
        )
        await self.users.create(user)
        return user

    async def attach_credentials(
        self,
        persona: Persona,
        email: str,
        password: str,
        actor: AuthUser,
        *,
        commit: bool = True,
    ) -> AuthUser:
        await self._assert_can_manage_credentials(actor, persona)
        user = await self._create_auth_user_record(persona, email, password)
        if commit:
            await self.session.commit()
        else:
            await self.session.flush()
        return user

    async def create_user(self, payload: AuthUserCreate, actor: AuthUser) -> AuthUser:
        persona = await self.personas.get(str(payload.persona_id))
        if not persona or persona.deleted_at is not None:
            raise DomainError("persona no encontrada", status_code=404)
        return await self.attach_credentials(
            persona,
            payload.email,
            payload.password,
            actor,
            commit=True,
        )

    async def set_password(self, persona_id: str, new_password: str, actor: AuthUser) -> None:
        persona = await self.personas.get(persona_id)
        if not persona or persona.deleted_at is not None:
            raise DomainError("persona no encontrada", status_code=404)
        await self._assert_can_manage_credentials(actor, persona)
        if persona.rol not in AUTHENTICABLE_PERSON_ROLES:
            raise DomainError("AMIGO no puede tener cuenta autenticable", status_code=422)
        user = persona.auth_user
        if user is None:
            raise DomainError("la persona no tiene cuenta de acceso", status_code=404)
        user.password_hash = hash_password(new_password)
        await self.session.commit()

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

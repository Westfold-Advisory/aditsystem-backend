from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import EstatusPersona
from aditsystem_backend.models.persona import Persona
from aditsystem_backend.repositories.persona import PersonaRepository
from aditsystem_backend.schemas.persona import PersonaCreate, PersonaUpdate
from aditsystem_backend.services.persona_hierarchy import validate_parent
from aditsystem_backend.services.persona_policy import PersonaPolicy


class PersonaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PersonaRepository(session)
        self.policy = PersonaPolicy(session)

    async def create(self, payload: PersonaCreate, actor: AuthUser) -> Persona:
        parent = await self._parent_or_404(payload.parent_persona_id)
        validate_parent(payload.rol, parent)
        await self.policy.assert_create(actor, payload.rol, parent)
        persona = Persona(
            **payload.model_dump(exclude={"parent_persona_id"}),
            parent_persona_id=str(payload.parent_persona_id) if payload.parent_persona_id else None,
            fecha_registro=datetime.now(UTC),
            estatus=EstatusPersona.ACTIVO,
        )
        await self.repo.create(persona)
        await self.session.commit()
        return persona

    async def get_or_404(self, persona_id: UUID) -> Persona:
        persona = await self.repo.get(str(persona_id))
        if not persona or persona.deleted_at is not None:
            raise DomainError("persona no encontrada", status_code=404)
        return persona

    async def get_authorized(self, persona_id: UUID, actor: AuthUser) -> Persona:
        persona = await self.get_or_404(persona_id)
        await self.policy.assert_manage(actor, persona)
        return persona

    async def children(self, persona_id: UUID, actor: AuthUser) -> list[Persona]:
        persona = await self.get_authorized(persona_id, actor)
        return await self.repo.list_children(persona.id)

    async def update(self, persona_id: UUID, payload: PersonaUpdate, actor: AuthUser) -> Persona:
        persona = await self.get_authorized(persona_id, actor)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(persona, field, value)
        await self.session.commit()
        await self.session.refresh(persona)
        return persona

    async def soft_delete(self, persona_id: UUID, actor: AuthUser) -> None:
        persona = await self.get_authorized(persona_id, actor)
        if persona.id == actor.persona_id:
            raise DomainError("no puedes darte de baja a ti mismo", status_code=422)
        persona.estatus = EstatusPersona.BAJA
        persona.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def _parent_or_404(self, parent_id: UUID | None) -> Persona | None:
        if parent_id is None:
            return None
        return await self.get_or_404(parent_id)

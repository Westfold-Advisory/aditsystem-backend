from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import EstatusPersona, UserRole
from aditsystem_backend.models.politico import Politico
from aditsystem_backend.models.user import User
from aditsystem_backend.repositories.politico import PoliticoRepository
from aditsystem_backend.schemas.politico import PoliticoCreate, PoliticoUpdate


class PoliticoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PoliticoRepository(session)

    async def create_politico(self, *, payload: PoliticoCreate, actor: User) -> Politico:
        if actor.role != UserRole.ADMIN:
            raise DomainError("solo ADMIN puede crear políticos", status_code=403)
        politico = Politico(
            **payload.model_dump(),
            estatus=EstatusPersona.ACTIVO,
        )
        await self.repo.create(politico)
        await self.session.commit()
        return politico

    async def get_politico_or_404(self, politico_id: UUID) -> Politico:
        politico = await self.repo.get(str(politico_id))
        if not politico or politico.deleted_at is not None:
            raise DomainError("político no encontrado", status_code=404)
        return politico

    async def list_politicos(self, actor: User) -> list[Politico]:
        if actor.role == UserRole.ADMIN:
            return await self.repo.list()
        if actor.role == UserRole.POLITICO and actor.politico_id:
            p = await self.repo.get(actor.politico_id)
            return [p] if p and p.deleted_at is None else []
        raise DomainError("acceso denegado", status_code=403)

    async def update_politico(
        self, *, politico_id: UUID, payload: PoliticoUpdate, actor: User
    ) -> Politico:
        politico = await self.get_politico_or_404(politico_id)
        self._assert_can_manage(actor, politico)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(politico, field, value)
        await self.repo.save(politico)
        await self.session.commit()
        return politico

    async def soft_delete(self, *, politico_id: UUID, actor: User) -> None:
        if actor.role != UserRole.ADMIN:
            raise DomainError("solo ADMIN puede dar de baja un político", status_code=403)
        politico = await self.get_politico_or_404(politico_id)
        politico.deleted_at = datetime.now(UTC)
        politico.estatus = EstatusPersona.BAJA
        await self.session.commit()

    def _assert_can_manage(self, actor: User, politico: Politico) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if actor.role == UserRole.POLITICO and actor.politico_id == politico.id:
            return
        raise DomainError("no tienes permisos sobre este político", status_code=403)

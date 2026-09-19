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
from aditsystem_backend.services import hierarchy as hier


class PoliticoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PoliticoRepository(session)

    async def create_politico(self, *, payload: PoliticoCreate, actor: User) -> Politico:
        if actor.role != UserRole.ADMIN:
            raise DomainError("solo ADMIN puede crear políticos", status_code=403)

        parent: Politico | None = None
        if payload.tipo is not None:
            parent = await self._resolve_parent(payload.parent_politico_id)
            hier.validate_tipo_and_parent(payload.tipo, parent)

        data = payload.model_dump(exclude={"parent_politico_id"})
        politico = Politico(
            **data,
            parent_politico_id=str(payload.parent_politico_id) if payload.parent_politico_id else None,
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
        if actor.role in {UserRole.GENERAL_COORDINATOR, UserRole.COORDINATOR}:
            if actor.politico_id:
                p = await self.repo.get(actor.politico_id)
                return [p] if p and p.deleted_at is None else []
        raise DomainError("acceso denegado", status_code=403)

    async def update_politico(
        self, *, politico_id: UUID, payload: PoliticoUpdate, actor: User
    ) -> Politico:
        politico = await self.get_politico_or_404(politico_id)
        self._assert_can_manage(actor, politico)

        new_tipo = payload.tipo if payload.tipo is not None else politico.tipo
        new_parent_id_str: str | None = (
            str(payload.parent_politico_id) if payload.parent_politico_id is not None
            else politico.parent_politico_id
        )

        if new_tipo is not None and (payload.tipo is not None or payload.parent_politico_id is not None):
            if new_parent_id_str is not None:
                await hier.detect_cycle(self.session, str(politico_id), new_parent_id_str)
            parent = await self._resolve_parent(
                UUID(new_parent_id_str) if new_parent_id_str else None
            )
            hier.validate_tipo_and_parent(new_tipo, parent)

        for field, value in payload.model_dump(exclude_unset=True, exclude={"parent_politico_id"}).items():
            setattr(politico, field, value)
        if "parent_politico_id" in payload.model_fields_set:
            politico.parent_politico_id = (
                str(payload.parent_politico_id) if payload.parent_politico_id else None
            )

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

    async def _resolve_parent(self, parent_politico_id: UUID | None) -> Politico | None:
        if parent_politico_id is None:
            return None
        parent = await self.repo.get(str(parent_politico_id))
        if not parent:
            raise DomainError("político padre no encontrado", status_code=404)
        return parent

    def _assert_can_manage(self, actor: User, politico: Politico) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if actor.role in {UserRole.GENERAL_COORDINATOR, UserRole.COORDINATOR}:
            if actor.politico_id == politico.id:
                return
        raise DomainError("no tienes permisos sobre este político", status_code=403)

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import EstatusPersona, UserRole
from aditsystem_backend.models.lider import Lider
from aditsystem_backend.models.politico import Politico
from aditsystem_backend.models.user import User
from aditsystem_backend.repositories.lider import LiderRepository
from aditsystem_backend.repositories.politico import PoliticoRepository
from aditsystem_backend.schemas.lider import LiderCreate, LiderUpdate
from aditsystem_backend.services.authorization import HierarchyAuthorizer


class LiderService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = LiderRepository(session)

    async def create_lider(self, *, payload: LiderCreate, actor: User) -> Lider:
        if actor.role not in {UserRole.ADMIN, UserRole.COORDINATOR}:
            raise DomainError("solo ADMIN o COORDINATOR pueden registrar enlaces", status_code=403)
        if actor.role == UserRole.COORDINATOR:
            if actor.politico_id != str(payload.politico_id):
                raise DomainError(
                    "solo puedes registrar enlaces bajo tu propio perfil", status_code=403
                )
        else:
            politico = await PoliticoRepository(self.session).get(str(payload.politico_id))
            if not politico or politico.deleted_at is not None:
                raise DomainError("coordinador no encontrado", status_code=404)

        lider = Lider(
            **{k: v for k, v in payload.model_dump().items() if k != "politico_id"},
            politico_id=str(payload.politico_id),
            estatus=EstatusPersona.ACTIVO,
        )
        await self.repo.create(lider)
        await self.session.commit()
        return lider

    async def get_lider_or_404(self, lider_id: UUID, actor: User) -> Lider:
        return await HierarchyAuthorizer(self.session, actor).assert_lider_id(str(lider_id))

    async def list_lideres(self, actor: User, politico_id: UUID | None = None) -> list[Lider]:
        if actor.role == UserRole.ADMIN:
            if politico_id:
                return await self.repo.list_by_politico(str(politico_id))
            return await self.repo.list()
        if actor.role in {UserRole.GENERAL_COORDINATOR, UserRole.COORDINATOR}:
            authorizer = HierarchyAuthorizer(self.session, actor)
            pid = str(politico_id) if politico_id else actor.politico_id
            if politico_id:
                result = await self.session.get(Politico, pid)
                if not result:
                    raise DomainError("político no encontrado", status_code=404)
                await authorizer.assert_politico(result)
                return await self.repo.list_by_politico(pid)
            return await self.repo.list_by_politicos(await authorizer.scoped_politico_ids())
        if actor.role == UserRole.LINK and actor.lider_id:
            lider = await self.repo.get(actor.lider_id)
            return [lider] if lider and lider.deleted_at is None else []
        raise DomainError("acceso denegado", status_code=403)

    async def update_lider(
        self, *, lider_id: UUID, payload: LiderUpdate, actor: User
    ) -> Lider:
        lider = await self.get_lider_or_404(lider_id, actor)
        self._assert_can_manage(actor, lider)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(lider, field, value)
        await self.repo.save(lider)
        await self.session.commit()
        return lider

    async def soft_delete(self, *, lider_id: UUID, actor: User) -> None:
        lider = await self.get_lider_or_404(lider_id, actor)
        self._assert_can_manage(actor, lider)
        lider.deleted_at = datetime.now(UTC)
        lider.estatus = EstatusPersona.BAJA
        await self.session.commit()

    def _assert_can_manage(self, actor: User, lider: Lider) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if actor.role in {UserRole.GENERAL_COORDINATOR, UserRole.COORDINATOR}:
            return
        if actor.role == UserRole.LINK and actor.lider_id == lider.id:
            return
        raise DomainError("no tienes permisos sobre este enlace", status_code=403)

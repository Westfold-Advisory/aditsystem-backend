from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.models.invitado import Invitado
from aditsystem_backend.models.user import User
from aditsystem_backend.repositories.invitado import InvitadoRepository
from aditsystem_backend.schemas.invitado import InvitadoCreate, InvitadoUpdate
from aditsystem_backend.services.authorization import HierarchyAuthorizer


class InvitadoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = InvitadoRepository(session)

    async def create_invitado(self, *, payload: InvitadoCreate, actor: User) -> Invitado:
        if actor.role not in {UserRole.ADMIN, UserRole.COORDINATOR, UserRole.LINK}:
            raise DomainError("no tienes permisos para registrar amigos", status_code=403)
        await HierarchyAuthorizer(self.session, actor).assert_lider_id(str(payload.lider_id))

        invitado = Invitado(
            **{k: v for k, v in payload.model_dump().items() if k != "lider_id"},
            lider_id=str(payload.lider_id),
        )
        await self.repo.create(invitado)
        await self.session.commit()
        return invitado

    async def get_invitado_or_404(self, invitado_id: UUID, actor: User) -> Invitado:
        return await HierarchyAuthorizer(self.session, actor).assert_invitado_id(str(invitado_id))

    async def list_invitados(
        self, actor: User, lider_id: UUID | None = None
    ) -> list[Invitado]:
        authorizer = HierarchyAuthorizer(self.session, actor)
        if actor.role == UserRole.ADMIN:
            if lider_id:
                return await self.repo.list_by_lider(str(lider_id))
            return await self.repo.list()
        if actor.role in {UserRole.GENERAL_COORDINATOR, UserRole.COORDINATOR}:
            if lider_id:
                await authorizer.assert_lider_id(str(lider_id))
                return await self.repo.list_by_lider(str(lider_id))
            return await self.repo.list_by_politicos(await authorizer.scoped_politico_ids())
        if actor.role == UserRole.LINK and actor.lider_id:
            lid = str(lider_id) if lider_id else actor.lider_id
            if lid != actor.lider_id:
                raise DomainError("acceso denegado", status_code=403)
            return await self.repo.list_by_lider(lid)
        if actor.role == UserRole.FRIEND and actor.invitado_id:
            inv = await self.repo.get(actor.invitado_id)
            return [inv] if inv and inv.deleted_at is None else []
        raise DomainError("acceso denegado", status_code=403)

    async def update_invitado(
        self, *, invitado_id: UUID, payload: InvitadoUpdate, actor: User
    ) -> Invitado:
        invitado = await self.get_invitado_or_404(invitado_id, actor)
        self._assert_can_manage(actor, invitado)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(invitado, field, value)
        await self.repo.save(invitado)
        await self.session.commit()
        return invitado

    async def soft_delete(self, *, invitado_id: UUID, actor: User) -> None:
        invitado = await self.get_invitado_or_404(invitado_id, actor)
        self._assert_can_manage(actor, invitado)
        invitado.deleted_at = datetime.now(UTC)
        await self.session.commit()

    def _assert_can_manage(self, actor: User, invitado: Invitado) -> None:
        if actor.role in {UserRole.ADMIN, UserRole.COORDINATOR, UserRole.LINK}:
            return
        raise DomainError("no tienes permisos sobre este amigo", status_code=403)

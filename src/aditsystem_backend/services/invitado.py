from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.models.invitado import Invitado
from aditsystem_backend.models.user import User
from aditsystem_backend.repositories.invitado import InvitadoRepository
from aditsystem_backend.repositories.lider import LiderRepository
from aditsystem_backend.schemas.invitado import InvitadoCreate, InvitadoUpdate


class InvitadoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = InvitadoRepository(session)

    async def create_invitado(self, *, payload: InvitadoCreate, actor: User) -> Invitado:
        if actor.role not in {UserRole.ADMIN, UserRole.COORDINATOR, UserRole.LINK}:
            raise DomainError("no tienes permisos para registrar amigos", status_code=403)
        if actor.role == UserRole.LINK:
            if actor.lider_id != str(payload.lider_id):
                raise DomainError(
                    "solo puedes registrar amigos bajo tu propio perfil", status_code=403
                )
        else:
            lider = await LiderRepository(self.session).get(str(payload.lider_id))
            if not lider or lider.deleted_at is not None:
                raise DomainError("enlace no encontrado", status_code=404)

        invitado = Invitado(
            **{k: v for k, v in payload.model_dump().items() if k != "lider_id"},
            lider_id=str(payload.lider_id),
        )
        await self.repo.create(invitado)
        await self.session.commit()
        return invitado

    async def get_invitado_or_404(self, invitado_id: UUID) -> Invitado:
        invitado = await self.repo.get(str(invitado_id))
        if not invitado or invitado.deleted_at is not None:
            raise DomainError("amigo no encontrado", status_code=404)
        return invitado

    async def list_invitados(
        self, actor: User, lider_id: UUID | None = None
    ) -> list[Invitado]:
        if actor.role == UserRole.ADMIN:
            if lider_id:
                return await self.repo.list_by_lider(str(lider_id))
            return await self.repo.list()
        if actor.role == UserRole.COORDINATOR and actor.politico_id:
            if lider_id:
                lider = await LiderRepository(self.session).get(str(lider_id))
                if not lider or lider.politico_id != actor.politico_id:
                    raise DomainError("acceso denegado", status_code=403)
                return await self.repo.list_by_lider(str(lider_id))
            return await self.repo.list()
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
        invitado = await self.get_invitado_or_404(invitado_id)
        self._assert_can_manage(actor, invitado)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(invitado, field, value)
        await self.repo.save(invitado)
        await self.session.commit()
        return invitado

    async def soft_delete(self, *, invitado_id: UUID, actor: User) -> None:
        invitado = await self.get_invitado_or_404(invitado_id)
        self._assert_can_manage(actor, invitado)
        invitado.deleted_at = datetime.now(UTC)
        await self.session.commit()

    def _assert_can_manage(self, actor: User, invitado: Invitado) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if actor.role == UserRole.LINK and actor.lider_id == invitado.lider_id:
            return
        if actor.role == UserRole.COORDINATOR:
            return
        raise DomainError("no tienes permisos sobre este amigo", status_code=403)

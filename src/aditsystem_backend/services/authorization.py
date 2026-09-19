"""Authorization based on both a role capability and resource ownership.

Out-of-scope existing resources consistently return 403. This avoids a
different policy between detail, mutation, document and collection endpoints.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.models.invitado import Invitado
from aditsystem_backend.models.lider import Lider
from aditsystem_backend.models.politico import Politico
from aditsystem_backend.models.user import User


class HierarchyAuthorizer:
    """Resolve the actor's subtree at the database boundary."""

    def __init__(self, session: AsyncSession, actor: User) -> None:
        self.session = session
        self.actor = actor

    @staticmethod
    def denied() -> DomainError:
        return DomainError("acceso denegado", status_code=403)

    async def scoped_politico_ids(self) -> set[str]:
        if self.actor.role == UserRole.ADMIN:
            result = await self.session.execute(
                select(Politico.id).where(Politico.deleted_at.is_(None))
            )
            return set(result.scalars())
        if not self.actor.politico_id:
            return set()
        if self.actor.role == UserRole.GENERAL_COORDINATOR:
            result = await self.session.execute(
                select(Politico.id).where(
                    Politico.deleted_at.is_(None),
                    (Politico.id == self.actor.politico_id)
                    | (Politico.parent_politico_id == self.actor.politico_id),
                )
            )
            return set(result.scalars())
        if self.actor.role == UserRole.COORDINATOR:
            return {self.actor.politico_id}
        return set()

    async def assert_politico(self, politico: Politico) -> None:
        if politico.id not in await self.scoped_politico_ids():
            raise self.denied()

    async def assert_lider(self, lider: Lider) -> None:
        if self.actor.role == UserRole.LINK and self.actor.lider_id == lider.id:
            return
        if lider.politico_id not in await self.scoped_politico_ids():
            raise self.denied()

    async def assert_invitado(self, invitado: Invitado) -> None:
        if self.actor.role == UserRole.FRIEND and self.actor.invitado_id == invitado.id:
            return
        result = await self.session.execute(
            select(Lider.politico_id).where(Lider.id == invitado.lider_id)
        )
        lider_politico_id = result.scalar_one_or_none()
        if self.actor.role == UserRole.LINK and self.actor.lider_id == invitado.lider_id:
            return
        if lider_politico_id not in await self.scoped_politico_ids():
            raise self.denied()

    async def assert_lider_id(self, lider_id: str) -> Lider:
        lider = await self.session.get(Lider, lider_id)
        if not lider or lider.deleted_at is not None:
            raise DomainError("enlace no encontrado", status_code=404)
        await self.assert_lider(lider)
        return lider

    async def assert_invitado_id(self, invitado_id: str) -> Invitado:
        invitado = await self.session.get(Invitado, invitado_id)
        if not invitado or invitado.deleted_at is not None:
            raise DomainError("amigo no encontrado", status_code=404)
        await self.assert_invitado(invitado)
        return invitado

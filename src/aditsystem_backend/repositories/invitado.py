from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.models.invitado import Invitado
from aditsystem_backend.models.lider import Lider


class InvitadoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, invitado: Invitado) -> Invitado:
        self.session.add(invitado)
        await self.session.flush()
        await self.session.refresh(invitado)
        return invitado

    async def get(self, invitado_id: str) -> Invitado | None:
        return await self.session.get(Invitado, invitado_id)

    async def list_by_lider(
        self, lider_id: str, include_deleted: bool = False
    ) -> list[Invitado]:
        stmt = select(Invitado).where(Invitado.lider_id == lider_id)
        if not include_deleted:
            stmt = stmt.where(Invitado.deleted_at.is_(None))
        result = await self.session.execute(stmt.order_by(Invitado.apellido_paterno))
        return list(result.scalars().all())

    async def list(self, include_deleted: bool = False) -> list[Invitado]:
        stmt = select(Invitado)
        if not include_deleted:
            stmt = stmt.where(Invitado.deleted_at.is_(None))
        result = await self.session.execute(stmt.order_by(Invitado.apellido_paterno))
        return list(result.scalars().all())

    async def list_by_politicos(self, politico_ids: set[str]) -> list[Invitado]:
        if not politico_ids:
            return []
        stmt = (
            select(Invitado)
            .join(Lider, Invitado.lider_id == Lider.id)
            .where(
                Lider.politico_id.in_(politico_ids),
                Lider.deleted_at.is_(None),
                Invitado.deleted_at.is_(None),
            )
        )
        result = await self.session.execute(stmt.order_by(Invitado.apellido_paterno))
        return list(result.scalars().all())

    async def save(self, invitado: Invitado) -> Invitado:
        await self.session.flush()
        await self.session.refresh(invitado)
        return invitado

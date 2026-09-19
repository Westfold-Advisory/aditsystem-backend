from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.models.politico import Politico


class PoliticoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, politico: Politico) -> Politico:
        self.session.add(politico)
        await self.session.flush()
        await self.session.refresh(politico)
        return politico

    async def get(self, politico_id: str) -> Politico | None:
        return await self.session.get(Politico, politico_id)

    async def list(self, include_deleted: bool = False) -> list[Politico]:
        stmt = select(Politico)
        if not include_deleted:
            stmt = stmt.where(Politico.deleted_at.is_(None))
        result = await self.session.execute(stmt.order_by(Politico.apellido_paterno))
        return list(result.scalars().all())

    async def list_by_ids(self, politico_ids: set[str]) -> list[Politico]:
        if not politico_ids:
            return []
        stmt = select(Politico).where(
            Politico.id.in_(politico_ids), Politico.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt.order_by(Politico.apellido_paterno))
        return list(result.scalars().all())

    async def save(self, politico: Politico) -> Politico:
        await self.session.flush()
        await self.session.refresh(politico)
        return politico

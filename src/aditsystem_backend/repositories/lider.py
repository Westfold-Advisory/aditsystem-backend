from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.models.lider import Lider


class LiderRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, lider: Lider) -> Lider:
        self.session.add(lider)
        await self.session.flush()
        await self.session.refresh(lider)
        return lider

    async def get(self, lider_id: str) -> Lider | None:
        return await self.session.get(Lider, lider_id)

    async def list_by_politico(
        self, politico_id: str, include_deleted: bool = False
    ) -> list[Lider]:
        stmt = select(Lider).where(Lider.politico_id == politico_id)
        if not include_deleted:
            stmt = stmt.where(Lider.deleted_at.is_(None))
        result = await self.session.execute(stmt.order_by(Lider.apellido_paterno))
        return list(result.scalars().all())

    async def list(self, include_deleted: bool = False) -> list[Lider]:
        stmt = select(Lider)
        if not include_deleted:
            stmt = stmt.where(Lider.deleted_at.is_(None))
        result = await self.session.execute(stmt.order_by(Lider.apellido_paterno))
        return list(result.scalars().all())

    async def list_by_politicos(self, politico_ids: set[str]) -> list[Lider]:
        if not politico_ids:
            return []
        stmt = select(Lider).where(
            Lider.politico_id.in_(politico_ids), Lider.deleted_at.is_(None)
        )
        result = await self.session.execute(stmt.order_by(Lider.apellido_paterno))
        return list(result.scalars().all())

    async def save(self, lider: Lider) -> Lider:
        await self.session.flush()
        await self.session.refresh(lider)
        return lider

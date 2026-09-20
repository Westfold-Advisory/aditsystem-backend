from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.models.documento import Documento
from aditsystem_backend.models.enums import DocumentoTipo


class DocumentoRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, documento: Documento) -> Documento:
        self.session.add(documento)
        await self.session.flush()
        await self.session.refresh(documento)
        return documento

    async def get(self, documento_id: str) -> Documento | None:
        return await self.session.get(Documento, documento_id)

    async def list_by_persona(
        self,
        persona_id: str,
        tipo: DocumentoTipo | None = None,
        include_deleted: bool = False,
    ) -> list[Documento]:
        stmt = select(Documento).where(
            Documento.persona_id == persona_id,
        )
        if tipo:
            stmt = stmt.where(Documento.tipo == tipo)
        if not include_deleted:
            stmt = stmt.where(Documento.deleted_at.is_(None))
        result = await self.session.execute(
            stmt.order_by(Documento.tipo, Documento.version.desc())
        )
        return list(result.scalars().all())

    async def retire_previous_versions(
        self, persona_id: str, tipo: DocumentoTipo
    ) -> None:
        """Mark all active documents of the same type as not-current before uploading a new version."""
        stmt = (
            update(Documento)
            .where(
                Documento.persona_id == persona_id,
                Documento.tipo == tipo,
                Documento.is_current.is_(True),
                Documento.deleted_at.is_(None),
            )
            .values(is_current=False)
        )
        await self.session.execute(stmt)

    async def next_version(self, persona_id: str, tipo: DocumentoTipo) -> int:
        docs = await self.list_by_persona(persona_id, tipo, include_deleted=True)
        if not docs:
            return 1
        return max(d.version for d in docs) + 1

    async def save(self, documento: Documento) -> Documento:
        await self.session.flush()
        await self.session.refresh(documento)
        return documento

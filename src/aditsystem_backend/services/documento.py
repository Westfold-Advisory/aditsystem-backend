from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.documento import Documento
from aditsystem_backend.models.enums import DocumentoTipo, EntityType, UserRole
from aditsystem_backend.models.user import User
from aditsystem_backend.repositories.documento import DocumentoRepository
from aditsystem_backend.schemas.documento import DocumentoCreate


class DocumentoService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = DocumentoRepository(session)

    async def register_documento(
        self, *, payload: DocumentoCreate, actor: User
    ) -> Documento:
        """Register document metadata after the binary has been uploaded to S3 by the caller."""
        self._assert_can_write(actor, payload.entity_type, str(payload.entity_id))
        version = await self.repo.next_version(
            payload.entity_type, str(payload.entity_id), payload.tipo
        )
        await self.repo.retire_previous_versions(
            payload.entity_type, str(payload.entity_id), payload.tipo
        )
        documento = Documento(
            entity_type=payload.entity_type,
            entity_id=str(payload.entity_id),
            tipo=payload.tipo,
            titulo=payload.titulo,
            descripcion=payload.descripcion,
            version=version,
            s3_key=payload.s3_key,
            mime_type=payload.mime_type,
            size_bytes=payload.size_bytes,
            is_current=True,
            subido_por=actor.id,
        )
        await self.repo.create(documento)
        await self.session.commit()
        return documento

    async def list_documentos(
        self,
        *,
        entity_type: EntityType,
        entity_id: UUID,
        tipo: DocumentoTipo | None,
        actor: User,
    ) -> list[Documento]:
        self._assert_can_read(actor, entity_type, str(entity_id))
        return await self.repo.list_by_entity(entity_type, str(entity_id), tipo)

    async def get_documento_or_404(self, documento_id: UUID, actor: User) -> Documento:
        doc = await self.repo.get(str(documento_id))
        if not doc or doc.deleted_at is not None:
            raise DomainError("documento no encontrado", status_code=404)
        self._assert_can_read(actor, EntityType(doc.entity_type), doc.entity_id)
        return doc

    async def soft_delete(self, *, documento_id: UUID, actor: User) -> None:
        doc = await self.repo.get(str(documento_id))
        if not doc or doc.deleted_at is not None:
            raise DomainError("documento no encontrado", status_code=404)
        self._assert_can_write(actor, EntityType(doc.entity_type), doc.entity_id)
        doc.deleted_at = datetime.now(UTC)
        doc.is_current = False
        await self.session.commit()

    def _assert_can_read(self, actor: User, entity_type: EntityType, entity_id: str) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if entity_type == EntityType.POLITICO:
            if actor.role == UserRole.POLITICO and actor.politico_id == entity_id:
                return
        elif entity_type == EntityType.LIDER:
            if actor.role in {UserRole.ADMIN, UserRole.POLITICO, UserRole.LIDER}:
                if actor.role == UserRole.LIDER and actor.lider_id != entity_id:
                    raise DomainError("acceso denegado", status_code=403)
                return
        elif entity_type == EntityType.INVITADO:
            if actor.role in {UserRole.ADMIN, UserRole.POLITICO, UserRole.LIDER}:
                return
            if actor.role == UserRole.INVITADO and actor.invitado_id == entity_id:
                return
        raise DomainError("acceso denegado", status_code=403)

    def _assert_can_write(self, actor: User, entity_type: EntityType, entity_id: str) -> None:
        if actor.role == UserRole.ADMIN:
            return
        if entity_type == EntityType.POLITICO:
            if actor.role == UserRole.POLITICO and actor.politico_id == entity_id:
                return
        elif entity_type == EntityType.LIDER:
            if actor.role == UserRole.POLITICO:
                return
            if actor.role == UserRole.LIDER and actor.lider_id == entity_id:
                return
        elif entity_type == EntityType.INVITADO:
            if actor.role in {UserRole.POLITICO, UserRole.LIDER}:
                return
        raise DomainError("no tienes permisos para gestionar este documento", status_code=403)

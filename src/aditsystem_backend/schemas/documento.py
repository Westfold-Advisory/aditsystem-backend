from datetime import datetime
from uuid import UUID

from pydantic import Field

from aditsystem_backend.models.enums import DocumentoTipo, EntityType
from aditsystem_backend.schemas.common import APIModel, UUIDModel


class DocumentoCreate(APIModel):
    entity_type: EntityType
    entity_id: UUID
    tipo: DocumentoTipo
    titulo: str = Field(min_length=1, max_length=255)
    descripcion: str | None = None
    s3_key: str = Field(min_length=1, max_length=1000)
    mime_type: str = Field(min_length=1, max_length=127)
    size_bytes: int = Field(gt=0)


class DocumentoRead(UUIDModel):
    entity_type: EntityType
    entity_id: UUID
    tipo: DocumentoTipo
    titulo: str
    descripcion: str | None
    version: int
    s3_key: str
    mime_type: str
    size_bytes: int
    is_current: bool
    subido_por: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class DocumentoList(UUIDModel):
    entity_type: EntityType
    entity_id: UUID
    tipo: DocumentoTipo
    titulo: str
    version: int
    mime_type: str
    size_bytes: int
    is_current: bool
    created_at: datetime

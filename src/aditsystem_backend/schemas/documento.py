from datetime import datetime
from uuid import UUID

from pydantic import Field

from aditsystem_backend.models.enums import DocumentoTipo
from aditsystem_backend.schemas.common import APIModel, UUIDModel


class PersonaDocumentoCreate(APIModel):
    tipo: DocumentoTipo
    titulo: str = Field(min_length=1, max_length=255)
    descripcion: str | None = None
    s3_key: str = Field(min_length=1, max_length=1000)
    mime_type: str = Field(min_length=1, max_length=127)
    size_bytes: int = Field(gt=0)


class DocumentoRead(UUIDModel):
    persona_id: UUID
    tipo: DocumentoTipo
    titulo: str
    descripcion: str | None
    version: int
    s3_key: str
    mime_type: str
    size_bytes: int
    is_current: bool
    subido_por_persona_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class DocumentoList(UUIDModel):
    persona_id: UUID
    tipo: DocumentoTipo
    titulo: str
    version: int
    mime_type: str
    size_bytes: int
    is_current: bool
    created_at: datetime


class DocumentoDownload(APIModel):
    """URL firmada de descarga; no expone la clave de almacenamiento privado."""

    url: str
    expires_at: datetime
    file_name: str

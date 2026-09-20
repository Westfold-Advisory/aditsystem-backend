from sqlalchemy import Boolean, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import (
    Base,
    SoftDeleteModel,
    TimestampedModel,
    UUIDPrimaryKey,
)
from aditsystem_backend.models.enums import DocumentoTipo


class Documento(UUIDPrimaryKey, TimestampedModel, SoftDeleteModel, Base):
    """Versionable document/CV metadata. Binary lives in private S3; only s3_key is stored."""

    __tablename__ = "documentos"

    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    subido_por_persona_id: Mapped[str] = mapped_column(
        ForeignKey("personas.id"), index=True
    )
    tipo: Mapped[str] = mapped_column(
        Enum(DocumentoTipo, name="documento_tipo"), nullable=False
    )
    titulo: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    s3_key: Mapped[str] = mapped_column(String(1000), nullable=False)
    mime_type: Mapped[str] = mapped_column(String(127), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    persona = relationship("Persona", foreign_keys=[persona_id])
    subido_por_persona = relationship("Persona", foreign_keys=[subido_por_persona_id])

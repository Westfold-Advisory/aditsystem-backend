from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, SoftDeleteModel, TimestampedModel, UUIDPrimaryKey
from aditsystem_backend.models.enums import PersonRole


class Persona(UUIDPrimaryKey, TimestampedModel, SoftDeleteModel, Base):
    """Single ownership tree; credential material never belongs to AMIGO."""

    __tablename__ = "personas"
    __table_args__ = (
        CheckConstraint("parent_persona_id IS NULL OR parent_persona_id != id", name="no_self_parent"),
        CheckConstraint("latitud IS NULL OR (latitud >= -90 AND latitud <= 90)", name="latitud_range"),
        CheckConstraint("longitud IS NULL OR (longitud >= -180 AND longitud <= 180)", name="longitud_range"),
    )

    rol: Mapped[PersonRole] = mapped_column(Enum(PersonRole, name="person_role"), nullable=False, index=True)
    parent_persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_materno: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    estatus: Mapped[str] = mapped_column(String(30), default="ACTIVO", nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    perfil_academico: Mapped[str | None] = mapped_column(String(255))
    equipo: Mapped[str | None] = mapped_column(String(255))
    contacto: Mapped[str | None] = mapped_column(String(255))
    seccion: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(255))
    latitud: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[float | None] = mapped_column(Numeric(10, 6))

    parent: Mapped["Persona | None"] = relationship("Persona", remote_side="Persona.id", back_populates="children")
    children: Mapped[list["Persona"]] = relationship("Persona", back_populates="parent")
    auth_user: Mapped["AuthUser | None"] = relationship("AuthUser", back_populates="persona", uselist=False)

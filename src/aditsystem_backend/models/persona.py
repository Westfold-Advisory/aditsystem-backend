from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, SoftDeleteModel, TimestampedModel, UUIDPrimaryKey
from aditsystem_backend.models.enums import NecesidadComunidad, PersonRole

if TYPE_CHECKING:
    from aditsystem_backend.models.auth_user import AuthUser
    from aditsystem_backend.models.persona_necesidad_comunidad import PersonaNecesidadComunidad


class Persona(UUIDPrimaryKey, TimestampedModel, SoftDeleteModel, Base):
    """Single ownership tree; credential material never belongs to AMIGO."""

    __tablename__ = "personas"
    __table_args__ = (
        CheckConstraint("parent_persona_id IS NULL OR parent_persona_id != id", name="no_self_parent"),
        CheckConstraint(
            "(latitud IS NULL AND longitud IS NULL) OR (latitud IS NOT NULL AND longitud IS NOT NULL)",
            name="persona_coords_pair",
        ),
        CheckConstraint("latitud IS NULL OR (latitud >= -90 AND latitud <= 90)", name="persona_latitud_range"),
        CheckConstraint(
            "longitud IS NULL OR (longitud >= -180 AND longitud <= 180)",
            name="persona_longitud_range",
        ),
    )

    rol: Mapped[PersonRole] = mapped_column(Enum(PersonRole, name="person_role"), nullable=False, index=True)
    parent_persona_id: Mapped[str | None] = mapped_column(ForeignKey("personas.id"), index=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_materno: Mapped[str] = mapped_column(String(120), nullable=False)
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    calle: Mapped[str | None] = mapped_column(String(200))
    numero_exterior: Mapped[str | None] = mapped_column(String(30))
    numero_interior: Mapped[str | None] = mapped_column(String(30))
    colonia: Mapped[str | None] = mapped_column(String(120))
    codigo_postal: Mapped[str | None] = mapped_column(String(10))
    entre_calles: Mapped[str | None] = mapped_column(String(255))
    latitud: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[float | None] = mapped_column(Numeric(10, 6))
    estatus: Mapped[str] = mapped_column(String(30), default="ACTIVO", nullable=False)
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    parent: Mapped["Persona | None"] = relationship("Persona", remote_side="Persona.id", back_populates="children")
    children: Mapped[list["Persona"]] = relationship("Persona", back_populates="parent")
    auth_user: Mapped["AuthUser | None"] = relationship("AuthUser", back_populates="persona", uselist=False)
    necesidades_comunidad_rows: Mapped[list["PersonaNecesidadComunidad"]] = relationship(
        "PersonaNecesidadComunidad",
        back_populates="persona",
        cascade="all, delete-orphan",
    )

    @property
    def necesidades_comunidad(self) -> list[NecesidadComunidad]:
        return [row.necesidad for row in self.necesidades_comunidad_rows]

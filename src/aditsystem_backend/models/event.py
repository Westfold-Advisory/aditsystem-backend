from datetime import datetime

from geoalchemy2 import Geography, WKTElement
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship, validates

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.db.base import (
    Base,
    SoftDeleteModel,
    TimestampedModel,
    UUIDPrimaryKey,
)
from aditsystem_backend.models.enums import EventStatus


class Event(UUIDPrimaryKey, TimestampedModel, SoftDeleteModel, Base):
    __tablename__ = "events"
    __table_args__ = (
        CheckConstraint("latitud >= -90 AND latitud <= 90", name="latitud_range"),
        CheckConstraint("longitud >= -180 AND longitud <= 180", name="longitud_range"),
        CheckConstraint(
            "capacidad_maxima IS NULL OR capacidad_maxima > 0",
            name="capacidad_mayor_a_cero",
        ),
        CheckConstraint(
            "checkin_radio_metros IS NULL OR checkin_radio_metros > 0",
            name="radio_mayor_a_cero",
        ),
        Index("ix_events_ubicacion", "ubicacion", postgresql_using="gist"),
    )

    # Persona is the durable business owner; AuthUser is credential-only.
    created_by_persona_id: Mapped[str] = mapped_column(
        ForeignKey("personas.id"), index=True
    )
    tipo: Mapped[str] = mapped_column(String(120), nullable=False)
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    latitud: Mapped[float] = mapped_column(Numeric(9, 6), nullable=False)
    longitud: Mapped[float] = mapped_column(Numeric(10, 6), nullable=False)
    ubicacion_texto: Mapped[str] = mapped_column(String(255), nullable=False)
    url_mapa: Mapped[str | None] = mapped_column(String(500))
    fecha_inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_fin: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    estatus: Mapped[EventStatus] = mapped_column(
        Enum(EventStatus, name="event_status"),
        default=EventStatus.BORRADOR,
        nullable=False,
    )
    capacidad_maxima: Mapped[int | None] = mapped_column(Integer)
    requiere_checkin: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )
    checkin_abierto_desde: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    checkin_abierto_hasta: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    checkin_radio_metros: Mapped[int | None] = mapped_column(Integer, default=100)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ubicacion: Mapped[str] = mapped_column(
        Geography("POINT", srid=4326), nullable=False
    )

    __mapper_args__ = {"version_id_col": version}

    creator_persona = relationship("Persona", foreign_keys=[created_by_persona_id])
    invitations = relationship("EventInvitation", back_populates="event")
    attendances = relationship("EventAttendance", back_populates="event")
    qr_tokens = relationship("EventCheckinToken", back_populates="event")

    @validates("latitud")
    def validate_latitud(self, _: str, value: float) -> float:
        if value < -90 or value > 90:
            raise DomainError("latitud debe estar entre -90 y 90")
        return value

    @validates("longitud")
    def validate_longitud(self, _: str, value: float) -> float:
        if value < -180 or value > 180:
            raise DomainError("longitud debe estar entre -180 y 180")
        return value

    def validate_temporal_rules(self) -> None:
        if self.fecha_fin <= self.fecha_inicio:
            raise DomainError("fecha_fin debe ser posterior a fecha_inicio")
        if self.checkin_abierto_desde and self.checkin_abierto_hasta:
            if self.checkin_abierto_hasta <= self.checkin_abierto_desde:
                raise DomainError(
                    "checkin_abierto_hasta debe ser posterior a checkin_abierto_desde"
                )

    def sync_geography(self) -> None:
        self.ubicacion = WKTElement(f"POINT({self.longitud} {self.latitud})", srid=4326)

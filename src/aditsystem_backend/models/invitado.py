from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, UUIDPrimaryKey
from aditsystem_backend.models.profile_mixins import GeoAddressMixin, PersonNameMixin


class Invitado(UUIDPrimaryKey, PersonNameMixin, GeoAddressMixin, Base):
    __tablename__ = "invitados"

    gestor_id: Mapped[str] = mapped_column(ForeignKey("gestores.id"), nullable=False, index=True)
    url_mapa: Mapped[str | None] = mapped_column(String(500))
    estatus: Mapped[str | None] = mapped_column(String(120))
    fuente_registro: Mapped[str | None] = mapped_column(String(120))
    codigo_invitacion: Mapped[str | None] = mapped_column(String(255), unique=True)
    evento_origen_id: Mapped[str | None] = mapped_column(String(36), index=True)
    asistencias_totales: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    ultimo_evento: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    gestor = relationship("Gestor", back_populates="invitados")
    invitations = relationship("EventInvitation", back_populates="invitado")
    attendances = relationship("EventAttendance", back_populates="invitado")

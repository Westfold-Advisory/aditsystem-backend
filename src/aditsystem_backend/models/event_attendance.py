from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, TimestampedModel, UUIDPrimaryKey
from aditsystem_backend.models.enums import AttendanceStatus, CheckinMethod


class EventAttendance(UUIDPrimaryKey, TimestampedModel, Base):
    __tablename__ = "event_attendances"
    __table_args__ = (
        UniqueConstraint("evento_id", "invitado_id", name="uq_event_attendance_event_invitado"),
    )

    evento_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    invitado_id: Mapped[str] = mapped_column(ForeignKey("invitados.id"), nullable=False, index=True)
    invitacion_id: Mapped[str] = mapped_column(
        ForeignKey("event_invitations.id"), nullable=False, unique=True
    )
    estatus: Mapped[AttendanceStatus] = mapped_column(
        Enum(AttendanceStatus, name="attendance_status"),
        default=AttendanceStatus.INVITADO,
        nullable=False,
    )
    checkin_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkout_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    checkin_metodo: Mapped[CheckinMethod | None] = mapped_column(
        Enum(CheckinMethod, name="checkin_method")
    )
    checkin_latitud: Mapped[float | None] = mapped_column(Numeric(9, 6))
    checkin_longitud: Mapped[float | None] = mapped_column(Numeric(10, 6))
    distancia_evento_metros: Mapped[float | None] = mapped_column(Numeric(10, 2))
    registrado_por: Mapped[str | None] = mapped_column(ForeignKey("users.id"))
    dispositivo_id: Mapped[str | None] = mapped_column(String(255))
    ip_address: Mapped[str | None] = mapped_column(String(64))
    user_agent: Mapped[str | None] = mapped_column(String(500))

    event = relationship("Event", back_populates="attendances")
    invitado = relationship("Invitado", back_populates="attendances")
    invitation = relationship("EventInvitation", back_populates="attendance")

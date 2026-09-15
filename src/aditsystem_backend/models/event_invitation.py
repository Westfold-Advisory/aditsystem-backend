from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, TimestampedModel, UUIDPrimaryKey
from aditsystem_backend.models.enums import InvitationStatus


class EventInvitation(UUIDPrimaryKey, TimestampedModel, Base):
    __tablename__ = "event_invitations"
    __table_args__ = (
        UniqueConstraint("evento_id", "invitado_id", name="uq_event_invitation_event_invitado"),
        UniqueConstraint("codigo_invitacion", name="uq_event_invitation_code"),
    )

    evento_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    invitado_id: Mapped[str] = mapped_column(ForeignKey("invitados.id"), nullable=False, index=True)
    invitado_por: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    estatus: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, name="invitation_status"),
        default=InvitationStatus.PENDIENTE,
        nullable=False,
    )
    codigo_invitacion: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_invitacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fecha_respuesta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str | None] = mapped_column(Text)

    event = relationship("Event", back_populates="invitations")
    invitado = relationship("Invitado", back_populates="invitations")
    attendance = relationship("EventAttendance", back_populates="invitation", uselist=False)

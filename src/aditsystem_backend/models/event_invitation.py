from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, TimestampedModel, UUIDPrimaryKey
from aditsystem_backend.models.enums import InvitationStatus


class EventInvitation(UUIDPrimaryKey, TimestampedModel, Base):
    __tablename__ = "event_invitations"
    __table_args__ = (
        UniqueConstraint(
            "evento_id", "persona_id", name="uq_event_invitation_event_persona"
        ),
        UniqueConstraint("codigo_invitacion", name="uq_event_invitation_code"),
    )

    evento_id: Mapped[str] = mapped_column(
        ForeignKey("events.id"), nullable=False, index=True
    )
    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), index=True)
    invitado_por_persona_id: Mapped[str] = mapped_column(
        ForeignKey("personas.id"), index=True
    )
    estatus: Mapped[InvitationStatus] = mapped_column(
        Enum(InvitationStatus, name="invitation_status"),
        default=InvitationStatus.PENDIENTE,
        nullable=False,
    )
    codigo_invitacion: Mapped[str] = mapped_column(String(255), nullable=False)
    fecha_invitacion: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    fecha_respuesta: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    observaciones: Mapped[str | None] = mapped_column(Text)

    event = relationship("Event", back_populates="invitations")
    attendance = relationship(
        "EventAttendance", back_populates="invitation", uselist=False
    )
    persona = relationship("Persona", foreign_keys=[persona_id])
    invitado_por_persona = relationship(
        "Persona", foreign_keys=[invitado_por_persona_id]
    )

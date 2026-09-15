from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, TimestampedModel, UUIDPrimaryKey


class EventCheckinToken(UUIDPrimaryKey, TimestampedModel, Base):
    __tablename__ = "event_checkin_tokens"
    __table_args__ = (UniqueConstraint("jti", name="uq_event_checkin_token_jti"),)

    event_id: Mapped[str] = mapped_column(ForeignKey("events.id"), nullable=False, index=True)
    jti: Mapped[str] = mapped_column(nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    event = relationship("Event", back_populates="qr_tokens")

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, TimestampedModel, UUIDPrimaryKey


class PersonaGeocerca(UUIDPrimaryKey, TimestampedModel, Base):
    """Explicit territory assignment; never inferred from an address string."""

    __tablename__ = "persona_geocercas"
    __table_args__ = (UniqueConstraint("persona_id", "geocerca_id", name="uq_persona_geocerca"),)

    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id"), nullable=False, index=True)
    geocerca_id: Mapped[str] = mapped_column(ForeignKey("geocercas.id"), nullable=False, index=True)

    persona = relationship("Persona")
    geocerca = relationship("Geocerca")

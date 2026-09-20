from sqlalchemy import Enum, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base
from aditsystem_backend.models.enums import NecesidadComunidad


class PersonaNecesidadComunidad(Base):
    __tablename__ = "persona_necesidades_comunidad"
    __table_args__ = (
        PrimaryKeyConstraint("persona_id", "necesidad", name="pk_persona_necesidad_comunidad"),
    )

    persona_id: Mapped[str] = mapped_column(ForeignKey("personas.id", ondelete="CASCADE"), index=True)
    necesidad: Mapped[NecesidadComunidad] = mapped_column(
        Enum(NecesidadComunidad, name="necesidad_comunidad"),
        nullable=False,
    )

    persona = relationship("Persona", back_populates="necesidades_comunidad_rows")

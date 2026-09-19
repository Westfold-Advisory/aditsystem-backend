from sqlalchemy import CheckConstraint, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import (
    Base,
    SoftDeleteModel,
    TimestampedModel,
    UUIDPrimaryKey,
)
from aditsystem_backend.models.enums import TipoPolitico
from aditsystem_backend.models.profile_mixins import GeoAddressMixin, PersonNameMixin


class Politico(UUIDPrimaryKey, PersonNameMixin, GeoAddressMixin, TimestampedModel, SoftDeleteModel, Base):
    __tablename__ = "politicos"
    __table_args__ = (
        CheckConstraint("parent_politico_id != id", name="no_self_parent"),
    )

    estatus: Mapped[str | None] = mapped_column(String(60))

    # Hierarchy fields (TRA-87): General Coordinator → Coordinator
    tipo: Mapped[str | None] = mapped_column(
        Enum(TipoPolitico, name="tipo_politico", create_type=False),
        nullable=True,
    )
    parent_politico_id: Mapped[str | None] = mapped_column(
        ForeignKey("politicos.id", name="fk_politicos_parent_politico_id_politicos"),
        index=True,
        nullable=True,
    )

    # Self-referential: Coordinator → its General Coordinator parent
    parent: Mapped["Politico | None"] = relationship(
        "Politico",
        foreign_keys="[Politico.parent_politico_id]",
        back_populates="coordinadores",
        remote_side="Politico.id",
    )
    # Self-referential: General Coordinator → its Coordinators
    coordinadores: Mapped[list["Politico"]] = relationship(
        "Politico",
        foreign_keys="[Politico.parent_politico_id]",
        back_populates="parent",
    )

    lideres = relationship("Lider", back_populates="politico")

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import (
    Base,
    SoftDeleteModel,
    TimestampedModel,
    UUIDPrimaryKey,
)
from aditsystem_backend.models.profile_mixins import GeoAddressMixin, PersonNameMixin


class Politico(UUIDPrimaryKey, PersonNameMixin, GeoAddressMixin, TimestampedModel, SoftDeleteModel, Base):
    __tablename__ = "politicos"

    estatus: Mapped[str | None] = mapped_column(String(60))

    lideres = relationship("Lider", back_populates="politico")

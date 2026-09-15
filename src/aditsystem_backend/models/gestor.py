from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from aditsystem_backend.db.base import Base, UUIDPrimaryKey
from aditsystem_backend.models.profile_mixins import GeoAddressMixin, PersonNameMixin


class Gestor(UUIDPrimaryKey, PersonNameMixin, GeoAddressMixin, Base):
    __tablename__ = "gestores"

    politico_id: Mapped[str] = mapped_column(ForeignKey("politicos.id"), nullable=False, index=True)
    url_mapa: Mapped[str | None] = mapped_column(String(500))

    politico = relationship("Politico", back_populates="gestores")
    invitados = relationship("Invitado", back_populates="gestor")

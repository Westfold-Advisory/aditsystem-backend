from sqlalchemy.orm import relationship

from aditsystem_backend.db.base import Base, UUIDPrimaryKey
from aditsystem_backend.models.profile_mixins import GeoAddressMixin, PersonNameMixin


class Politico(UUIDPrimaryKey, PersonNameMixin, GeoAddressMixin, Base):
    __tablename__ = "politicos"

    lideres = relationship("Lider", back_populates="politico")

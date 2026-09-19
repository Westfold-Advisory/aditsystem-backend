from datetime import UTC, datetime

from geoalchemy2 import Geometry
from sqlalchemy import Boolean, DateTime, Enum, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from aditsystem_backend.db.base import Base, TimestampedModel, UUIDPrimaryKey
from aditsystem_backend.models.enums import TipoGeocerca


class Geocerca(UUIDPrimaryKey, TimestampedModel, Base):
    """Versioned geospatial boundary (state, municipality, or district)."""

    __tablename__ = "geocercas"
    __table_args__ = (
        Index("ix_geocercas_geometria", "geometria", postgresql_using="gist"),
        UniqueConstraint("hash_geometria", "tipo", name="uq_geocerca_hash_tipo"),
    )

    tipo: Mapped[TipoGeocerca] = mapped_column(
        Enum(TipoGeocerca, name="tipo_geocerca"), nullable=False, index=True
    )
    nombre: Mapped[str] = mapped_column(String(255), nullable=False)
    codigo: Mapped[str | None] = mapped_column(String(50), index=True)
    codigo_padre: Mapped[str | None] = mapped_column(String(50), index=True)
    geometria: Mapped[object] = mapped_column(
        Geometry("GEOMETRY", srid=4326), nullable=False
    )
    fuente: Mapped[str] = mapped_column(String(255), nullable=False)
    hash_geometria: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    vigente: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, index=True)
    importado_en: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        nullable=False,
    )
    importado_por: Mapped[str | None] = mapped_column(String(100))

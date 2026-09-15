from datetime import datetime

from sqlalchemy import DateTime, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column


class PersonNameMixin:
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(120), nullable=False)
    apellido_materno: Mapped[str] = mapped_column(String(120), nullable=False)


class GeoAddressMixin:
    telefono: Mapped[str] = mapped_column(String(30), nullable=False)
    perfil_academico: Mapped[str | None] = mapped_column(String(255))
    equipo: Mapped[str | None] = mapped_column(String(255))
    enlace: Mapped[str | None] = mapped_column(String(255))
    municipio: Mapped[str | None] = mapped_column(String(120))
    distrito: Mapped[str | None] = mapped_column(String(120))
    seccion: Mapped[str | None] = mapped_column(String(120))
    direccion: Mapped[str | None] = mapped_column(String(255))
    latitud: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitud: Mapped[float | None] = mapped_column(Numeric(10, 6))
    url_imagen: Mapped[str | None] = mapped_column(String(500))
    url_cv: Mapped[str | None] = mapped_column(String(500))
    fecha_registro: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

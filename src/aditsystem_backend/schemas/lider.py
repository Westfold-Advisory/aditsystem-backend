from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from aditsystem_backend.models.enums import EstatusPersona
from aditsystem_backend.schemas.common import APIModel, UUIDModel


class LiderBase(APIModel):
    nombre: str = Field(min_length=1, max_length=120)
    apellido_paterno: str = Field(min_length=1, max_length=120)
    apellido_materno: str = Field(min_length=1, max_length=120)
    telefono: str = Field(min_length=1, max_length=30)
    perfil_academico: str | None = Field(default=None, max_length=255)
    equipo: str | None = Field(default=None, max_length=255)
    enlace: str | None = Field(default=None, max_length=255)
    municipio: str | None = Field(default=None, max_length=120)
    distrito: str | None = Field(default=None, max_length=120)
    seccion: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=255)
    latitud: Decimal | None = Field(default=None, ge=-90, le=90)
    longitud: Decimal | None = Field(default=None, ge=-180, le=180)
    url_imagen: str | None = Field(default=None, max_length=500)
    url_mapa: str | None = Field(default=None, max_length=500)
    fecha_registro: datetime


class LiderCreate(LiderBase):
    politico_id: UUID


class LiderUpdate(APIModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellido_paterno: str | None = Field(default=None, min_length=1, max_length=120)
    apellido_materno: str | None = Field(default=None, min_length=1, max_length=120)
    telefono: str | None = Field(default=None, min_length=1, max_length=30)
    perfil_academico: str | None = None
    equipo: str | None = None
    enlace: str | None = None
    municipio: str | None = None
    distrito: str | None = None
    seccion: str | None = None
    direccion: str | None = None
    latitud: Decimal | None = Field(default=None, ge=-90, le=90)
    longitud: Decimal | None = Field(default=None, ge=-180, le=180)
    url_imagen: str | None = None
    url_mapa: str | None = None
    estatus: EstatusPersona | None = None


class LiderRead(UUIDModel):
    politico_id: UUID
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    telefono: str
    perfil_academico: str | None
    equipo: str | None
    enlace: str | None
    municipio: str | None
    distrito: str | None
    seccion: str | None
    direccion: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    url_imagen: str | None
    url_cv: str | None
    url_mapa: str | None
    fecha_registro: datetime
    estatus: str | None
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class LiderList(UUIDModel):
    politico_id: UUID
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    telefono: str
    municipio: str | None
    distrito: str | None
    estatus: str | None
    created_at: datetime

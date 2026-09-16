from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from aditsystem_backend.schemas.common import APIModel, UUIDModel


class InvitadoBase(APIModel):
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
    estatus: str | None = Field(default=None, max_length=120)
    fuente_registro: str | None = Field(default=None, max_length=120)
    fecha_registro: datetime


class InvitadoCreate(InvitadoBase):
    lider_id: UUID


class InvitadoUpdate(APIModel):
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
    estatus: str | None = None


class InvitadoRead(UUIDModel):
    lider_id: UUID
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
    estatus: str | None
    fuente_registro: str | None
    asistencias_totales: int
    ultimo_evento: datetime | None
    fecha_registro: datetime
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class InvitadoList(UUIDModel):
    lider_id: UUID
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    telefono: str
    municipio: str | None
    estatus: str | None
    asistencias_totales: int
    created_at: datetime

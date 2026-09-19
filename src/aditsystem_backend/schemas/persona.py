from datetime import datetime
from uuid import UUID

from pydantic import Field

from aditsystem_backend.models.enums import EstatusPersona, PersonRole
from aditsystem_backend.schemas.common import APIModel, UUIDModel


class PersonaCreate(APIModel):
    rol: PersonRole
    parent_persona_id: UUID | None = None
    nombre: str = Field(min_length=1, max_length=120)
    apellido_paterno: str = Field(min_length=1, max_length=120)
    apellido_materno: str = Field(min_length=1, max_length=120)
    telefono: str = Field(min_length=1, max_length=30)
    perfil_academico: str | None = Field(default=None, max_length=255)
    equipo: str | None = Field(default=None, max_length=255)
    contacto: str | None = Field(default=None, max_length=255)
    seccion: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=255)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)


class PersonaUpdate(APIModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellido_paterno: str | None = Field(default=None, min_length=1, max_length=120)
    apellido_materno: str | None = Field(default=None, min_length=1, max_length=120)
    telefono: str | None = Field(default=None, min_length=1, max_length=30)
    estatus: EstatusPersona | None = None
    perfil_academico: str | None = Field(default=None, max_length=255)
    equipo: str | None = Field(default=None, max_length=255)
    contacto: str | None = Field(default=None, max_length=255)
    seccion: str | None = Field(default=None, max_length=120)
    direccion: str | None = Field(default=None, max_length=255)
    latitud: float | None = Field(default=None, ge=-90, le=90)
    longitud: float | None = Field(default=None, ge=-180, le=180)


class PersonaRead(UUIDModel):
    rol: PersonRole
    parent_persona_id: UUID | None
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    telefono: str
    estatus: EstatusPersona
    fecha_registro: datetime
    perfil_academico: str | None
    equipo: str | None
    contacto: str | None
    seccion: str | None
    direccion: str | None
    latitud: float | None
    longitud: float | None
    created_at: datetime
    updated_at: datetime

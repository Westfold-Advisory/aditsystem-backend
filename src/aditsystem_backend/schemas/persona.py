from datetime import datetime
from uuid import UUID

from pydantic import Field

from aditsystem_backend.models.enums import EstatusPersona, PersonRole
from aditsystem_backend.schemas.common import APIModel, UUIDModel
from aditsystem_backend.schemas.geocerca import GeocercaRead


class PersonaCreate(APIModel):
    rol: PersonRole
    parent_persona_id: UUID | None = None
    nombre: str = Field(min_length=1, max_length=120)
    apellido_paterno: str = Field(min_length=1, max_length=120)
    apellido_materno: str = Field(min_length=1, max_length=120)
    telefono: str = Field(min_length=1, max_length=30)


class PersonaUpdate(APIModel):
    nombre: str | None = Field(default=None, min_length=1, max_length=120)
    apellido_paterno: str | None = Field(default=None, min_length=1, max_length=120)
    apellido_materno: str | None = Field(default=None, min_length=1, max_length=120)
    telefono: str | None = Field(default=None, min_length=1, max_length=30)
    estatus: EstatusPersona | None = None


class PersonaRead(UUIDModel):
    rol: PersonRole
    parent_persona_id: UUID | None
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    telefono: str
    estatus: EstatusPersona
    fecha_registro: datetime
    created_at: datetime
    updated_at: datetime


class PersonaMetricas(APIModel):
    descendientes: int
    coordinadores: int
    enlaces: int
    amigos: int
    documentos: int
    eventos_creados: int
    invitaciones: int
    asistencias: int


class PersonaMapaEntrada(APIModel):
    persona_id: UUID
    rol: PersonRole
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    geocercas: list[GeocercaRead]


class PersonaMapaScoped(APIModel):
    root_persona_id: UUID
    personas: list[PersonaMapaEntrada]

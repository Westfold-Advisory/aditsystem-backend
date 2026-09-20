from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field

from aditsystem_backend.models.enums import EstatusPersona, NecesidadComunidad, PersonRole
from aditsystem_backend.schemas.common import APIModel, UUIDModel
from aditsystem_backend.schemas.geocerca import GeocercaRead
from aditsystem_backend.schemas.persona_direccion import NecesidadesComunidadMixin, PersonaDireccionFields


class PersonaCreate(PersonaDireccionFields, NecesidadesComunidadMixin):
    rol: PersonRole
    parent_persona_id: UUID | None = None
    nombre: str = Field(min_length=1, max_length=120)
    apellido_paterno: str = Field(min_length=1, max_length=120)
    apellido_materno: str = Field(min_length=1, max_length=120)
    telefono: str = Field(min_length=1, max_length=30)


class PersonaUpdate(PersonaDireccionFields, NecesidadesComunidadMixin):
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
    calle: str | None
    numero_exterior: str | None
    numero_interior: str | None
    colonia: str | None
    codigo_postal: str | None
    entre_calles: str | None
    latitud: Decimal | None
    longitud: Decimal | None
    necesidades_comunidad: list[NecesidadComunidad]
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
    latitud: Decimal | None = None
    longitud: Decimal | None = None
    geocercas: list[GeocercaRead]


class PersonaMapaScoped(APIModel):
    root_persona_id: UUID
    personas: list[PersonaMapaEntrada]


class CoberturaMapPin(APIModel):
    persona_id: UUID
    rol: PersonRole
    nombre: str
    apellido_paterno: str
    apellido_materno: str
    latitud: Decimal
    longitud: Decimal


class CoberturaHeatmapCell(APIModel):
    latitud: Decimal
    longitud: Decimal
    necesidad: NecesidadComunidad
    intensidad: int = Field(ge=1)


class PersonaMapaCobertura(APIModel):
    root_persona_id: UUID
    pines: list[CoberturaMapPin]
    heatmap: list[CoberturaHeatmapCell]

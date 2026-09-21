from datetime import datetime
from decimal import Decimal
from typing import Self
from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from aditsystem_backend.models.enums import (
    AUTHENTICABLE_PERSON_ROLES,
    EstatusPersona,
    NecesidadComunidad,
    PersonRole,
)
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
    email: EmailStr | None = None
    password: str | None = Field(default=None, min_length=8, max_length=128)

    @model_validator(mode="after")
    def validate_credentials_for_role(self) -> Self:
        needs_account = self.rol in AUTHENTICABLE_PERSON_ROLES
        has_any = self.email is not None or self.password is not None
        if needs_account:
            if self.email is None or self.password is None:
                raise ValueError("email y contraseña son obligatorios para este rol")
        elif has_any:
            raise ValueError("AMIGO no admite credenciales de acceso")
        return self


class PersonaPasswordUpdate(APIModel):
    new_password: str = Field(min_length=8, max_length=128)


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

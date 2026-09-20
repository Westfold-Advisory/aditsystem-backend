from decimal import Decimal

from pydantic import Field, field_validator, model_validator

from aditsystem_backend.models.enums import MAX_NECESIDADES_COMUNIDAD_POR_PERSONA, NecesidadComunidad
from aditsystem_backend.schemas.common import APIModel


class PersonaDireccionFields(APIModel):
    calle: str | None = Field(default=None, max_length=200)
    numero_exterior: str | None = Field(default=None, max_length=30)
    numero_interior: str | None = Field(default=None, max_length=30)
    colonia: str | None = Field(default=None, max_length=120)
    codigo_postal: str | None = Field(default=None, max_length=10)
    entre_calles: str | None = Field(default=None, max_length=255)
    latitud: Decimal | None = Field(default=None, ge=-90, le=90)
    longitud: Decimal | None = Field(default=None, ge=-180, le=180)

    @model_validator(mode="after")
    def validate_coordinate_pair(self) -> "PersonaDireccionFields":
        has_lat = self.latitud is not None
        has_lng = self.longitud is not None
        if has_lat ^ has_lng:
            raise ValueError("latitud y longitud deben enviarse juntas o omitirse")
        return self


def validate_necesidades_comunidad(values: list[NecesidadComunidad] | None) -> list[NecesidadComunidad] | None:
    if values is None:
        return None
    unique = list(dict.fromkeys(values))
    if len(unique) > MAX_NECESIDADES_COMUNIDAD_POR_PERSONA:
        raise ValueError(
            f"máximo {MAX_NECESIDADES_COMUNIDAD_POR_PERSONA} necesidades de la comunidad por persona"
        )
    return unique


class NecesidadesComunidadMixin(APIModel):
    necesidades_comunidad: list[NecesidadComunidad] | None = None

    @field_validator("necesidades_comunidad")
    @classmethod
    def cap_necesidades(cls, value: list[NecesidadComunidad] | None) -> list[NecesidadComunidad] | None:
        return validate_necesidades_comunidad(value)

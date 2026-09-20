from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from aditsystem_backend.models.enums import EventStatus
from aditsystem_backend.schemas.common import UTCDateRangeModel, UUIDModel


class EventBase(UTCDateRangeModel):
    tipo: str = Field(min_length=1, max_length=120)
    nombre: str = Field(min_length=1, max_length=255)
    descripcion: str = Field(min_length=1)
    latitud: Decimal = Field(ge=-90, le=90)
    longitud: Decimal = Field(ge=-180, le=180)
    ubicacion_texto: str = Field(min_length=1, max_length=255)
    url_mapa: str | None = Field(default=None, max_length=500)
    fecha_inicio: datetime
    fecha_fin: datetime
    capacidad_maxima: int | None = Field(default=None, gt=0)
    requiere_checkin: bool = True
    checkin_abierto_desde: datetime | None = None
    checkin_abierto_hasta: datetime | None = None
    checkin_radio_metros: int | None = Field(default=100, gt=0)

    @model_validator(mode="after")
    def validate_temporal_rules(self) -> "EventBase":
        if self.fecha_fin <= self.fecha_inicio:
            raise ValueError("fecha_fin debe ser posterior a fecha_inicio")
        if self.checkin_abierto_desde and self.checkin_abierto_hasta:
            if self.checkin_abierto_hasta <= self.checkin_abierto_desde:
                raise ValueError(
                    "checkin_abierto_hasta debe ser posterior a checkin_abierto_desde"
                )
        return self


class EventCreate(EventBase):
    pass


class EventUpdate(UTCDateRangeModel):
    tipo: str | None = Field(default=None, min_length=1, max_length=120)
    nombre: str | None = Field(default=None, min_length=1, max_length=255)
    descripcion: str | None = None
    latitud: Decimal | None = Field(default=None, ge=-90, le=90)
    longitud: Decimal | None = Field(default=None, ge=-180, le=180)
    ubicacion_texto: str | None = Field(default=None, min_length=1, max_length=255)
    url_mapa: str | None = Field(default=None, max_length=500)
    fecha_inicio: datetime | None = None
    fecha_fin: datetime | None = None
    capacidad_maxima: int | None = Field(default=None, gt=0)
    requiere_checkin: bool | None = None
    checkin_abierto_desde: datetime | None = None
    checkin_abierto_hasta: datetime | None = None
    checkin_radio_metros: int | None = Field(default=None, gt=0)


class EventRead(UUIDModel):
    created_by: UUID | None
    created_by_persona_id: UUID | None
    tipo: str
    nombre: str
    descripcion: str
    latitud: Decimal
    longitud: Decimal
    ubicacion_texto: str
    url_mapa: str | None
    fecha_inicio: datetime
    fecha_fin: datetime
    estatus: EventStatus
    capacidad_maxima: int | None
    requiere_checkin: bool
    checkin_abierto_desde: datetime | None
    checkin_abierto_hasta: datetime | None
    checkin_radio_metros: int | None
    version: int
    created_at: datetime
    updated_at: datetime
    deleted_at: datetime | None


class EventQRCodeRead(UTCDateRangeModel):
    token: str
    jti: UUID
    event_id: UUID
    expires_at: datetime

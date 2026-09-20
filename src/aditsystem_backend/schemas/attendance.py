from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, model_validator

from aditsystem_backend.models.enums import AttendanceStatus, CheckinMethod
from aditsystem_backend.schemas.common import UTCDateRangeModel, UUIDModel


class AttendanceRead(UUIDModel):
    evento_id: UUID
    persona_id: UUID
    invitacion_id: UUID
    estatus: AttendanceStatus
    checkin_at: datetime | None
    checkout_at: datetime | None
    checkin_metodo: CheckinMethod | None
    checkin_latitud: Decimal | None
    checkin_longitud: Decimal | None
    distancia_evento_metros: Decimal | None
    registrado_por_persona_id: UUID | None
    dispositivo_id: str | None
    ip_address: str | None
    user_agent: str | None
    created_at: datetime
    updated_at: datetime


class QRCheckinRequest(UTCDateRangeModel):
    token: str
    dispositivo_id: str | None = Field(default=None, max_length=255)


class GeoCheckinRequest(UTCDateRangeModel):
    latitud: Decimal = Field(ge=-90, le=90)
    longitud: Decimal = Field(ge=-180, le=180)
    precision_metros: Decimal = Field(gt=0)
    dispositivo_id: str | None = Field(default=None, max_length=255)


class ManualCheckinRequest(UTCDateRangeModel):
    persona_id: UUID
    metodo: CheckinMethod = CheckinMethod.MANUAL
    dispositivo_id: str | None = Field(default=None, max_length=255)
    latitud: Decimal | None = Field(default=None, ge=-90, le=90)
    longitud: Decimal | None = Field(default=None, ge=-180, le=180)


class CheckoutRequest(UTCDateRangeModel):
    checkout_at: datetime

    @model_validator(mode="after")
    def validate_checkout(self) -> "CheckoutRequest":
        return self

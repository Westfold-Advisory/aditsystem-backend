from datetime import UTC, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class APIModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class UUIDModel(APIModel):
    id: UUID


def ensure_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        raise ValueError("datetime debe incluir timezone")
    return value.astimezone(UTC)


class UTCDateRangeModel(APIModel):
    @field_validator(
        "fecha_inicio",
        "fecha_fin",
        "checkin_abierto_desde",
        "checkin_abierto_hasta",
        "fecha_invitacion",
        "fecha_respuesta",
        "checkin_at",
        "checkout_at",
        check_fields=False,
    )
    @classmethod
    def validate_datetime(cls, value: datetime | None) -> datetime | None:
        return ensure_utc(value)

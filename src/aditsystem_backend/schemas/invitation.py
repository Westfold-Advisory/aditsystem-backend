from datetime import datetime
from uuid import UUID

from pydantic import Field

from aditsystem_backend.models.enums import InvitationStatus
from aditsystem_backend.schemas.common import UTCDateRangeModel, UUIDModel


class InvitationCreate(UTCDateRangeModel):
    persona_id: UUID
    observaciones: str | None = Field(default=None, max_length=500)


class InvitationResponseUpdate(UTCDateRangeModel):
    estatus: InvitationStatus
    observaciones: str | None = Field(default=None, max_length=500)


class InvitationRead(UUIDModel):
    evento_id: UUID
    persona_id: UUID
    invitado_por_persona_id: UUID
    estatus: InvitationStatus
    codigo_invitacion: str
    fecha_invitacion: datetime
    fecha_respuesta: datetime | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime

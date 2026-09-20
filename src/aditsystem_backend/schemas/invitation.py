from datetime import datetime
from uuid import UUID

from pydantic import Field

from aditsystem_backend.models.enums import InvitationStatus
from aditsystem_backend.schemas.common import UTCDateRangeModel, UUIDModel


class InvitationCreate(UTCDateRangeModel):
    invitado_id: UUID
    observaciones: str | None = Field(default=None, max_length=500)


class InvitationResponseUpdate(UTCDateRangeModel):
    estatus: InvitationStatus
    observaciones: str | None = Field(default=None, max_length=500)


class InvitationRead(UUIDModel):
    evento_id: UUID
    invitado_id: UUID | None
    invitado_por: UUID | None
    persona_id: UUID | None
    invitado_por_persona_id: UUID | None
    estatus: InvitationStatus
    codigo_invitacion: str
    fecha_invitacion: datetime
    fecha_respuesta: datetime | None
    observaciones: str | None
    created_at: datetime
    updated_at: datetime

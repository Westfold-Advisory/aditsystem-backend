from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.schemas.common import APIModel, UTCDateRangeModel, UUIDModel


class UserCreate(APIModel):
    """Public self-registration schema. Role is always INVITADO; privileged fields excluded."""
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    invitado_id: UUID | None = None


class AdminUserCreate(APIModel):
    """Admin-only schema for creating users with any role and entity associations."""
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole = UserRole.INVITADO
    politico_id: UUID | None = None
    gestor_id: UUID | None = None
    invitado_id: UUID | None = None


class UserLogin(APIModel):
    email: EmailStr
    password: str


class UserRead(UUIDModel):
    email: EmailStr
    full_name: str
    role: UserRole
    politico_id: UUID | None
    gestor_id: UUID | None
    invitado_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: UserRead

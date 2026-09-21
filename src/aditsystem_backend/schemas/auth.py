from datetime import datetime
from uuid import UUID

from pydantic import EmailStr, Field

from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.schemas.common import APIModel, UUIDModel


class AuthUserCreate(APIModel):
    """Credentials can only be assigned to an existing non-AMIGO Persona."""
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    persona_id: UUID


class UserLogin(APIModel):
    email: EmailStr
    password: str


class AuthUserRead(UUIDModel):
    # Plain str, not EmailStr: this is an output-only field echoing an
    # already-persisted address (validated at write time, or a trusted
    # seed/dev value like `@aditsystem.test`). Re-validating on the way out
    # would 500 GET /me and similar reads for any account whose email uses
    # an IANA reserved/special-use TLD that EmailStr rejects.
    email: str
    persona_id: UUID
    rol: PersonRole
    is_active: bool
    created_at: datetime
    updated_at: datetime


class TokenResponse(APIModel):
    access_token: str
    token_type: str = "bearer"
    expires_in_seconds: int
    user: AuthUserRead

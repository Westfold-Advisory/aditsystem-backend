from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import jwt
from passlib.context import CryptContext

from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.models.enums import PersonRole

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


@dataclass(slots=True)
class AccessTokenPayload:
    sub: UUID
    email: str
    role: PersonRole
    iat: datetime
    exp: datetime
    jti: str


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return pwd_context.verify(password, password_hash)


def create_access_token(
    *,
    subject: UUID,
    email: str,
    role: PersonRole,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    config = settings or get_settings()
    now = datetime.now(UTC)
    expiry = now + (expires_delta or timedelta(minutes=config.jwt_access_token_expire_minutes))
    payload = {
        "sub": str(subject),
        "email": email,
        "role": role,
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp()),
        "iss": config.jwt_issuer,
        "aud": config.jwt_audience,
        "jti": str(uuid4()),
        "type": "access",
    }
    return jwt.encode(payload, config.jwt_private_key, algorithm=config.jwt_algorithm)


def decode_access_token(token: str, settings: Settings | None = None) -> AccessTokenPayload:
    config = settings or get_settings()
    payload = jwt.decode(
        token,
        config.jwt_public_key,
        algorithms=[config.jwt_algorithm],
        audience=config.jwt_audience,
        issuer=config.jwt_issuer,
    )
    return AccessTokenPayload(
        sub=UUID(payload["sub"]),
        email=payload["email"],
        role=PersonRole(payload["role"]),
        iat=datetime.fromtimestamp(payload["iat"], tz=UTC),
        exp=datetime.fromtimestamp(payload["exp"], tz=UTC),
        jti=payload["jti"],
    )


def create_event_qr_token(
    *,
    event_id: UUID,
    jti: UUID,
    settings: Settings | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    config = settings or get_settings()
    now = datetime.now(UTC)
    expiry = now + (expires_delta or timedelta(seconds=config.event_qr_ttl_seconds))
    payload = {
        "event_id": str(event_id),
        "jti": str(jti),
        "type": "event_checkin",
        "iat": int(now.timestamp()),
        "exp": int(expiry.timestamp()),
        "iss": config.event_qr_issuer,
        "aud": config.event_qr_audience,
    }
    return jwt.encode(payload, config.jwt_private_key, algorithm=config.jwt_algorithm)


def decode_event_qr_token(token: str, settings: Settings | None = None) -> dict[str, str | int]:
    config = settings or get_settings()
    return jwt.decode(
        token,
        config.jwt_public_key,
        algorithms=[config.jwt_algorithm],
        audience=config.event_qr_audience,
        issuer=config.event_qr_issuer,
    )

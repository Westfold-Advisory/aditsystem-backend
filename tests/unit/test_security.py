from datetime import timedelta
from pathlib import Path
from uuid import uuid4

from aditsystem_backend.core.config import Settings
from aditsystem_backend.core.security import (
    create_access_token,
    create_event_qr_token,
    decode_access_token,
    decode_event_qr_token,
)


FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def build_settings() -> Settings:
    return Settings(
        jwt_private_key_path=FIXTURES_DIR / "jwt-private.pem",
        jwt_public_key_path=FIXTURES_DIR / "jwt-public.pem",
    )


def test_access_token_roundtrip() -> None:
    settings = build_settings()
    user_id = uuid4()

    token = create_access_token(
        subject=user_id,
        email="test@example.com",
        role="ADMIN",
        settings=settings,
        expires_delta=timedelta(minutes=5),
    )

    payload = decode_access_token(token, settings=settings)
    assert payload.sub == user_id
    assert payload.email == "test@example.com"
    assert payload.role == "ADMIN"


def test_event_qr_roundtrip() -> None:
    settings = build_settings()
    event_id = uuid4()
    jti = uuid4()

    token = create_event_qr_token(
        event_id=event_id,
        jti=jti,
        settings=settings,
        expires_delta=timedelta(seconds=120),
    )

    payload = decode_event_qr_token(token, settings=settings)
    assert payload["type"] == "event_checkin"
    assert payload["event_id"] == str(event_id)
    assert payload["jti"] == str(jti)

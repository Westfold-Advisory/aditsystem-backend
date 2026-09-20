from uuid import uuid4

from aditsystem_backend.schemas.auth import AuthUserCreate


def test_auth_user_create_is_bound_to_a_persona() -> None:
    persona_id = uuid4()
    payload = AuthUserCreate(
        email="coordinador@example.com", password="password123", persona_id=persona_id
    )

    assert payload.persona_id == persona_id
    assert not hasattr(payload, "role")
    assert not hasattr(payload, "invitado_id")

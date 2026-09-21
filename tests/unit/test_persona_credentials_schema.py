"""TRA-137/138: PersonaCreate must couple email+password to authenticable roles."""

import pytest
from pydantic import ValidationError

from aditsystem_backend.schemas.persona import PersonaCreate, PersonaPasswordUpdate

_BASE = {
    "nombre": "Ana",
    "apellido_paterno": "López",
    "apellido_materno": "Ruiz",
    "telefono": "2221234567",
}


def test_authenticable_role_requires_email_and_password() -> None:
    with pytest.raises(ValidationError, match="obligatorios"):
        PersonaCreate(rol="ENLACE", parent_persona_id=None, **_BASE)


def test_authenticable_role_rejects_email_without_password() -> None:
    with pytest.raises(ValidationError, match="obligatorios"):
        PersonaCreate(rol="ENLACE", parent_persona_id=None, email="a@example.com", **_BASE)


def test_authenticable_role_accepts_email_and_password() -> None:
    payload = PersonaCreate(
        rol="ENLACE",
        parent_persona_id=None,
        email="a@example.com",
        password="12345678",
        **_BASE,
    )
    assert payload.email == "a@example.com"


def test_authenticable_role_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        PersonaCreate(
            rol="ENLACE",
            parent_persona_id=None,
            email="a@example.com",
            password="1234567",
            **_BASE,
        )


def test_amigo_rejects_credentials() -> None:
    with pytest.raises(ValidationError, match="no admite credenciales"):
        PersonaCreate(
            rol="AMIGO",
            parent_persona_id=None,
            email="a@example.com",
            password="12345678",
            **_BASE,
        )


def test_amigo_without_credentials_is_valid() -> None:
    payload = PersonaCreate(rol="AMIGO", parent_persona_id=None, **_BASE)
    assert payload.email is None
    assert payload.password is None


def test_password_update_rejects_short_password() -> None:
    with pytest.raises(ValidationError):
        PersonaPasswordUpdate(new_password="1234567")


def test_password_update_accepts_min_length() -> None:
    assert PersonaPasswordUpdate(new_password="12345678").new_password == "12345678"

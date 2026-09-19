from uuid import uuid4

import pytest

from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.schemas.auth import AdminUserCreate, UserCreate


def test_user_create_ignores_role_field() -> None:
    data = {
        "email": "attacker@example.com",
        "full_name": "Attacker",
        "password": "password123",
        "role": "ADMIN",
    }
    user = UserCreate(**data)
    assert not hasattr(user, "role")


def test_user_create_ignores_politico_id() -> None:
    data = {
        "email": "test@example.com",
        "full_name": "Test",
        "password": "password123",
        "politico_id": str(uuid4()),
    }
    user = UserCreate(**data)
    assert not hasattr(user, "politico_id")


def test_user_create_ignores_lider_id() -> None:
    data = {
        "email": "test@example.com",
        "full_name": "Test",
        "password": "password123",
        "lider_id": str(uuid4()),
    }
    user = UserCreate(**data)
    assert not hasattr(user, "lider_id")


def test_user_create_accepts_invitado_id() -> None:
    iid = uuid4()
    user = UserCreate(
        email="guest@example.com",
        full_name="Guest",
        password="password123",
        invitado_id=iid,
    )
    assert user.invitado_id == iid


@pytest.mark.parametrize(
    "role",
    [UserRole.GENERAL_COORDINATOR, UserRole.COORDINATOR, UserRole.LINK, UserRole.ADMIN],
)
def test_admin_user_create_accepts_privileged_roles(role: UserRole) -> None:
    payload = AdminUserCreate(
        email=f"{role.lower()}@example.com",
        full_name="User",
        password="password123",
        role=role,
    )
    assert payload.role == role


def test_admin_user_create_defaults_to_friend() -> None:
    payload = AdminUserCreate(
        email="default@example.com",
        full_name="Default",
        password="password123",
    )
    assert payload.role == UserRole.FRIEND

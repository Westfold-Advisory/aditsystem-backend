from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.models.user import User
from aditsystem_backend.schemas.auth import AdminUserCreate, UserCreate
from aditsystem_backend.services.auth import AuthService


def make_service(existing_user: User | None = None) -> AuthService:
    session = AsyncMock()
    with patch("aditsystem_backend.services.auth.get_settings"):
        service = AuthService(session)
    service.users = AsyncMock()
    service.users.get_by_email = AsyncMock(return_value=existing_user)
    service.users.create = AsyncMock()
    return service


@pytest.fixture(autouse=True)
def _mock_hash_password(monkeypatch):
    monkeypatch.setattr(
        "aditsystem_backend.services.auth.hash_password",
        lambda pwd: f"hashed:{pwd}",
    )


def make_actor(role: UserRole) -> User:
    actor = MagicMock(spec=User)
    actor.role = role
    return actor


@pytest.mark.asyncio
async def test_register_always_assigns_invitado() -> None:
    service = make_service()
    payload = UserCreate(email="new@example.com", full_name="New User", password="password123")

    user = await service.register(payload)

    assert user.role == UserRole.INVITADO


@pytest.mark.asyncio
async def test_register_duplicate_email_raises_409() -> None:
    service = make_service(existing_user=MagicMock(spec=User))
    payload = UserCreate(email="dupe@example.com", full_name="Dupe", password="password123")

    with pytest.raises(DomainError) as exc_info:
        await service.register(payload)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
@pytest.mark.parametrize("role", [UserRole.POLITICO, UserRole.GESTOR, UserRole.INVITADO])
async def test_create_user_non_admin_actor_is_forbidden(role: UserRole) -> None:
    service = make_service()
    actor = make_actor(role)
    payload = AdminUserCreate(
        email="target@example.com",
        full_name="Target",
        password="password123",
        role=UserRole.POLITICO,
    )

    with pytest.raises(DomainError) as exc_info:
        await service.create_user(payload, actor)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
@pytest.mark.parametrize("target_role", [UserRole.POLITICO, UserRole.GESTOR, UserRole.ADMIN, UserRole.INVITADO])
async def test_create_user_admin_can_assign_any_role(target_role: UserRole) -> None:
    service = make_service()
    actor = make_actor(UserRole.ADMIN)
    payload = AdminUserCreate(
        email="user@example.com",
        full_name="User",
        password="password123",
        role=target_role,
    )

    user = await service.create_user(payload, actor)

    assert user.role == target_role


@pytest.mark.asyncio
async def test_create_user_admin_duplicate_email_raises_409() -> None:
    service = make_service(existing_user=MagicMock(spec=User))
    actor = make_actor(UserRole.ADMIN)
    payload = AdminUserCreate(
        email="dupe@example.com",
        full_name="Dupe",
        password="password123",
        role=UserRole.POLITICO,
    )

    with pytest.raises(DomainError) as exc_info:
        await service.create_user(payload, actor)

    assert exc_info.value.status_code == 409

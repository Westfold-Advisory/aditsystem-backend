from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.schemas.auth import AuthUserCreate
from aditsystem_backend.services.auth import AuthService


def make_service() -> AuthService:
    with patch("aditsystem_backend.services.auth.get_settings"):
        service = AuthService(AsyncMock())
    service.users = AsyncMock()
    service.personas = AsyncMock()
    return service


def actor(role: PersonRole, persona_id: str | None = None) -> AuthUser:
    value = MagicMock(spec=AuthUser)
    value.persona_id = persona_id or str(uuid4())
    value.persona = MagicMock(rol=role)
    return value


@pytest.mark.asyncio
async def test_enlace_cannot_delegate_account_creation() -> None:
    """ENLACE never manages credentials — TRA-137 delegates that only to ADMIN/CG/COORD."""
    service = make_service()
    service.users.get_by_email.return_value = None
    persona = MagicMock(id=str(uuid4()), deleted_at=None, rol=PersonRole.ENLACE, auth_user=None)
    service.personas.get.return_value = persona
    payload = AuthUserCreate(email="target@example.com", password="password123", persona_id=uuid4())

    with pytest.raises(DomainError) as error:
        await service.create_user(payload, actor(PersonRole.ENLACE))

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_coordinator_outside_scope_cannot_create_account() -> None:
    service = make_service()
    service.users.get_by_email.return_value = None
    persona = MagicMock(id=str(uuid4()), deleted_at=None, rol=PersonRole.ENLACE, auth_user=None)
    service.personas.get.return_value = persona
    service.policy._is_descendant = AsyncMock(return_value=False)
    payload = AuthUserCreate(email="target@example.com", password="password123", persona_id=uuid4())

    with pytest.raises(DomainError) as error:
        await service.create_user(payload, actor(PersonRole.COORDINADOR))

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_coordinator_in_scope_can_create_account() -> None:
    """TRA-137: delegated provisioning — COORDINADOR may attach credentials
    for an ENLACE in their own branch, not only ADMIN via /admin/users."""
    service = make_service()
    service.users.get_by_email.return_value = None
    service.users.get_by_persona_id.return_value = None
    persona = MagicMock(id=str(uuid4()), deleted_at=None, rol=PersonRole.ENLACE, auth_user=None)
    service.personas.get.return_value = persona
    service.policy._is_descendant = AsyncMock(return_value=True)
    payload = AuthUserCreate(email="target@example.com", password="password123", persona_id=uuid4())

    user = await service.create_user(payload, actor(PersonRole.COORDINADOR))

    assert user.email == "target@example.com"


@pytest.mark.asyncio
async def test_amigo_cannot_receive_credentials() -> None:
    service = make_service()
    service.users.get_by_email.return_value = None
    service.personas.get.return_value = MagicMock(
        id=str(uuid4()), deleted_at=None, rol=PersonRole.AMIGO, auth_user=None
    )
    payload = AuthUserCreate(email="amigo@example.com", password="password123", persona_id=uuid4())

    with pytest.raises(DomainError) as error:
        await service.create_user(payload, actor(PersonRole.ADMIN))

    assert error.value.status_code == 422


@pytest.mark.asyncio
async def test_inactive_or_amigo_account_cannot_login() -> None:
    service = make_service()
    user = MagicMock(spec=AuthUser)
    user.is_active = True
    user.persona = MagicMock(deleted_at=None, rol=PersonRole.AMIGO)
    service.users.get_by_email.return_value = user

    with pytest.raises(DomainError) as error:
        await service.login("amigo@example.com", "password123")

    assert error.value.status_code == 401

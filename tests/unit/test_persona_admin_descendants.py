from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.models.persona import Persona
from aditsystem_backend.services.persona import PersonaService


@pytest.mark.asyncio
async def test_admin_descendants_include_global_structure() -> None:
    admin_id = str(uuid4())
    admin_persona = MagicMock(spec=Persona, id=admin_id, deleted_at=None)
    actor = MagicMock(spec=AuthUser, persona_id=admin_id)
    actor.persona = admin_persona

    service = PersonaService(AsyncMock())
    service.get_or_404 = AsyncMock(return_value=admin_persona)
    service.policy.is_admin = MagicMock(return_value=True)
    service.repo.list_global_structure_excluding_admin = AsyncMock(
        return_value=[MagicMock(spec=Persona, rol=PersonRole.COORDINADOR_GENERAL)]
    )
    service.repo.list_descendants = AsyncMock(return_value=[])

    result = await service.descendants(uuid4(), actor)

    service.repo.list_global_structure_excluding_admin.assert_awaited_once_with(admin_id)
    service.repo.list_descendants.assert_not_awaited()
    assert len(result) == 1

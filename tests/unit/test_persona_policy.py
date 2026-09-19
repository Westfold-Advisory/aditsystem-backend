from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.models.persona import Persona
from aditsystem_backend.services.persona_policy import PersonaPolicy


def make_actor(role: PersonRole, persona_id: str) -> AuthUser:
    actor = MagicMock(spec=AuthUser)
    actor.persona_id = persona_id
    actor.persona = MagicMock(rol=role)
    return actor


@pytest.mark.asyncio
async def test_sibling_branch_is_denied_with_403() -> None:
    actor_id = str(uuid4())
    target = MagicMock(spec=Persona, id=str(uuid4()))
    policy = PersonaPolicy(AsyncMock())
    policy._is_descendant = AsyncMock(return_value=False)

    with pytest.raises(DomainError) as error:
        await policy.assert_manage(make_actor(PersonRole.COORDINADOR, actor_id), target)

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_direct_enlace_can_create_only_amigo_below_self() -> None:
    persona_id = str(uuid4())
    parent = MagicMock(spec=Persona, id=persona_id)
    policy = PersonaPolicy(AsyncMock())

    await policy.assert_create(make_actor(PersonRole.ENLACE, persona_id), PersonRole.AMIGO, parent)

    with pytest.raises(DomainError) as error:
        await policy.assert_create(make_actor(PersonRole.ENLACE, persona_id), PersonRole.ENLACE, parent)

    assert error.value.status_code == 403

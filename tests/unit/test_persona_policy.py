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
    policy.assert_manage = AsyncMock()

    await policy.assert_create(make_actor(PersonRole.ENLACE, persona_id), PersonRole.AMIGO, parent)

    with pytest.raises(DomainError) as error:
        await policy.assert_create(make_actor(PersonRole.ENLACE, persona_id), PersonRole.ENLACE, parent)

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_coordinador_general_can_create_enlace_under_coordinador_in_tree() -> None:
    cg_id = str(uuid4())
    coord_parent = MagicMock(spec=Persona, id=str(uuid4()))
    policy = PersonaPolicy(AsyncMock())
    policy.assert_manage = AsyncMock()

    await policy.assert_create(
        make_actor(PersonRole.COORDINADOR_GENERAL, cg_id),
        PersonRole.ENLACE,
        coord_parent,
    )
    policy.assert_manage.assert_awaited_once()


@pytest.mark.asyncio
async def test_coordinador_general_cannot_create_admin_or_another_general() -> None:
    policy = PersonaPolicy(AsyncMock())
    parent = MagicMock(spec=Persona, id=str(uuid4()))
    policy.assert_manage = AsyncMock()
    actor = make_actor(PersonRole.COORDINADOR_GENERAL, str(uuid4()))

    for forbidden in (PersonRole.ADMIN, PersonRole.COORDINADOR_GENERAL):
        with pytest.raises(DomainError) as error:
            await policy.assert_create(actor, forbidden, parent)
        assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_cannot_create_nested_admin() -> None:
    policy = PersonaPolicy(AsyncMock())
    parent = MagicMock(spec=Persona, id=str(uuid4()))

    with pytest.raises(DomainError) as error:
        await policy.assert_create(make_actor(PersonRole.ADMIN, str(uuid4())), PersonRole.ADMIN, parent)

    assert error.value.status_code == 403

"""Unit coverage for the ADMIN/branch visibility rule on GET /events.

The recursive Persona-tree walk itself (``_visible_creator_ids``) needs a
real Postgres CTE to mean anything, so it is exercised end-to-end in
``tests/integration/test_events_api.py``. Here we pin down the service-level
contract in isolation: who gets asked, and how the answer is used.
"""

from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.models.event import Event
from aditsystem_backend.services.event import EventService


def _make_actor(role: PersonRole, persona_id: str) -> AuthUser:
    actor = MagicMock(spec=AuthUser)
    actor.persona_id = persona_id
    actor.persona = MagicMock(rol=role)
    return actor


def _make_event(created_by_persona_id: str) -> Event:
    event = MagicMock(spec=Event)
    event.created_by_persona_id = created_by_persona_id
    event.deleted_at = None
    return event


def _service_returning(event: Event) -> EventService:
    svc = EventService(AsyncMock())
    svc.repo = AsyncMock()
    svc.repo.get = AsyncMock(return_value=event)
    return svc


@pytest.mark.asyncio
async def test_get_event_for_read_admin_bypasses_branch_scope() -> None:
    event = _make_event(str(uuid4()))
    svc = _service_returning(event)
    svc._visible_creator_ids = AsyncMock()

    result = await svc.get_event_for_read(uuid4(), _make_actor(PersonRole.ADMIN, str(uuid4())))

    assert result is event
    svc._visible_creator_ids.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_event_for_read_allows_actor_within_branch() -> None:
    actor_id = str(uuid4())
    creator_id = str(uuid4())
    event = _make_event(creator_id)
    svc = _service_returning(event)
    svc._visible_creator_ids = AsyncMock(return_value=[actor_id, creator_id])

    result = await svc.get_event_for_read(uuid4(), _make_actor(PersonRole.COORDINADOR, actor_id))

    assert result is event


@pytest.mark.asyncio
async def test_get_event_for_read_denies_actor_outside_branch() -> None:
    actor_id = str(uuid4())
    event = _make_event(str(uuid4()))
    svc = _service_returning(event)
    svc._visible_creator_ids = AsyncMock(return_value=[actor_id])

    with pytest.raises(DomainError) as error:
        await svc.get_event_for_read(uuid4(), _make_actor(PersonRole.COORDINADOR, actor_id))

    assert error.value.status_code == 403


@pytest.mark.asyncio
async def test_list_events_admin_sees_unfiltered_repo_list() -> None:
    svc = EventService(AsyncMock())
    svc.repo = AsyncMock()
    svc.repo.list = AsyncMock(return_value=["all"])
    svc._visible_creator_ids = AsyncMock()

    result = await svc.list_events(_make_actor(PersonRole.ADMIN, str(uuid4())))

    assert result == ["all"]
    svc.repo.list.assert_awaited_once()
    svc._visible_creator_ids.assert_not_awaited()


@pytest.mark.asyncio
async def test_list_events_non_admin_uses_scoped_repo_query() -> None:
    actor_id = str(uuid4())
    svc = EventService(AsyncMock())
    svc.repo = AsyncMock()
    svc.repo.list_scoped = AsyncMock(return_value=["scoped"])
    svc._visible_creator_ids = AsyncMock(return_value=[actor_id])

    result = await svc.list_events(_make_actor(PersonRole.ENLACE, actor_id))

    assert result == ["scoped"]
    svc.repo.list_scoped.assert_awaited_once_with([actor_id])

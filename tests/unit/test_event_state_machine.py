"""Tests for event state machine: transitions, permissions, and soft-delete."""
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import EVENT_TRANSITIONS, EventStatus, UserRole
from aditsystem_backend.models.event import Event
from aditsystem_backend.models.user import User
from aditsystem_backend.services.event import EventService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_event(estatus: EventStatus, owner_id: str | None = None) -> Event:
    e = MagicMock(spec=Event)
    e.id = str(uuid4())
    e.estatus = estatus
    e.deleted_at = None
    e.created_by = owner_id or str(uuid4())
    return e


def _make_user(role: UserRole, user_id: str | None = None) -> User:
    u = MagicMock(spec=User)
    u.id = user_id or str(uuid4())
    u.role = role
    u.invitado_id = None
    return u


def _service(event: Event) -> EventService:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()
    svc = EventService(session)
    svc.repo = AsyncMock()
    svc.get_event_or_404 = AsyncMock(return_value=event)
    return svc


# ---------------------------------------------------------------------------
# Transition map completeness
# ---------------------------------------------------------------------------

def test_all_statuses_present_in_transition_map() -> None:
    for status in EventStatus:
        assert status in EVENT_TRANSITIONS, f"{status} missing from EVENT_TRANSITIONS"


def test_terminal_states_have_no_transitions() -> None:
    assert EVENT_TRANSITIONS[EventStatus.FINALIZADO] == frozenset()
    assert EVENT_TRANSITIONS[EventStatus.CANCELADO] == frozenset()


# ---------------------------------------------------------------------------
# publish_event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_from_borrador_succeeds() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.BORRADOR, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    result = await svc.publish_event(event_id=uuid4(), actor=actor)

    assert result.estatus == EventStatus.PUBLICADO


@pytest.mark.asyncio
async def test_publish_from_publicado_fails() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.PUBLICADO, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    with pytest.raises(DomainError) as exc_info:
        await svc.publish_event(event_id=uuid4(), actor=actor)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_publish_from_cancelado_fails() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.CANCELADO, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    with pytest.raises(DomainError) as exc_info:
        await svc.publish_event(event_id=uuid4(), actor=actor)

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# unpublish_event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unpublish_from_publicado_succeeds() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.PUBLICADO, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    result = await svc.unpublish_event(event_id=uuid4(), actor=actor)

    assert result.estatus == EventStatus.BORRADOR


@pytest.mark.asyncio
async def test_unpublish_from_borrador_fails() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.BORRADOR, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    with pytest.raises(DomainError) as exc_info:
        await svc.unpublish_event(event_id=uuid4(), actor=actor)

    assert exc_info.value.status_code == 409


@pytest.mark.asyncio
async def test_unpublish_from_en_curso_fails() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.EN_CURSO, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    with pytest.raises(DomainError):
        await svc.unpublish_event(event_id=uuid4(), actor=actor)


# ---------------------------------------------------------------------------
# start_event / finish_event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_start_from_publicado_succeeds() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.PUBLICADO, owner_id)
    actor = _make_user(UserRole.LINK, owner_id)
    svc = _service(event)

    result = await svc.start_event(event_id=uuid4(), actor=actor)

    assert result.estatus == EventStatus.EN_CURSO


@pytest.mark.asyncio
async def test_finish_from_en_curso_succeeds() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.EN_CURSO, owner_id)
    actor = _make_user(UserRole.LINK, owner_id)
    svc = _service(event)

    result = await svc.finish_event(event_id=uuid4(), actor=actor)

    assert result.estatus == EventStatus.FINALIZADO


@pytest.mark.asyncio
async def test_finish_from_borrador_fails() -> None:
    owner_id = str(uuid4())
    event = _make_event(EventStatus.BORRADOR, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    with pytest.raises(DomainError) as exc_info:
        await svc.finish_event(event_id=uuid4(), actor=actor)

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# cancel_event
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "from_status",
    [EventStatus.BORRADOR, EventStatus.PUBLICADO, EventStatus.EN_CURSO],
)
async def test_cancel_from_cancellable_states(from_status: EventStatus) -> None:
    owner_id = str(uuid4())
    event = _make_event(from_status, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    result = await svc.cancel_event(event_id=uuid4(), actor=actor)

    assert result.estatus == EventStatus.CANCELADO


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "from_status",
    [EventStatus.FINALIZADO, EventStatus.CANCELADO],
)
async def test_cancel_from_terminal_states_fails(from_status: EventStatus) -> None:
    owner_id = str(uuid4())
    event = _make_event(from_status, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    with pytest.raises(DomainError) as exc_info:
        await svc.cancel_event(event_id=uuid4(), actor=actor)

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# delete_event (soft-delete / baja lógica)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize(
    "from_status",
    [EventStatus.BORRADOR, EventStatus.CANCELADO],
)
async def test_delete_allowed_for_borrador_and_cancelado(from_status: EventStatus) -> None:
    owner_id = str(uuid4())
    event = _make_event(from_status, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    await svc.delete_event(event_id=uuid4(), actor=actor)

    assert event.deleted_at is not None


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "from_status",
    [EventStatus.PUBLICADO, EventStatus.EN_CURSO, EventStatus.FINALIZADO],
)
async def test_delete_rejected_for_active_states(from_status: EventStatus) -> None:
    owner_id = str(uuid4())
    event = _make_event(from_status, owner_id)
    actor = _make_user(UserRole.COORDINATOR, owner_id)
    svc = _service(event)

    with pytest.raises(DomainError) as exc_info:
        await svc.delete_event(event_id=uuid4(), actor=actor)

    assert exc_info.value.status_code == 409


# ---------------------------------------------------------------------------
# Permission enforcement: non-owner cannot manage
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_publish_rejected_for_non_owner_politico() -> None:
    event = _make_event(EventStatus.BORRADOR, owner_id=str(uuid4()))
    actor = _make_user(UserRole.COORDINATOR, user_id=str(uuid4()))  # different id
    svc = _service(event)

    with pytest.raises(DomainError) as exc_info:
        await svc.publish_event(event_id=uuid4(), actor=actor)

    assert exc_info.value.status_code == 403


@pytest.mark.asyncio
async def test_admin_can_publish_any_event() -> None:
    event = _make_event(EventStatus.BORRADOR, owner_id=str(uuid4()))
    actor = _make_user(UserRole.ADMIN, user_id=str(uuid4()))
    svc = _service(event)

    result = await svc.publish_event(event_id=uuid4(), actor=actor)

    assert result.estatus == EventStatus.PUBLICADO


# ---------------------------------------------------------------------------
# Unpublished event is not visible publicly
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_unpublished_event_not_in_public_list() -> None:
    session = AsyncMock()
    svc = EventService(session)
    svc.repo = AsyncMock()
    svc.repo.list_public = AsyncMock(return_value=[])

    result = await svc.list_public_events()

    assert result == []
    svc.repo.list_public.assert_awaited_once()


@pytest.mark.asyncio
async def test_borrador_event_not_accessible_via_public_endpoint() -> None:
    session = AsyncMock()
    svc = EventService(session)
    svc.repo = AsyncMock()
    svc.repo.get_public = AsyncMock(return_value=None)

    with pytest.raises(DomainError) as exc_info:
        await svc.get_public_event_or_404(uuid4())

    assert exc_info.value.status_code == 404

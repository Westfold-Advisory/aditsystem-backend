from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import EventStatus
from aditsystem_backend.models.event import Event
from aditsystem_backend.services.event import EventService


def _make_event(estatus: EventStatus, deleted: bool = False) -> Event:
    e = MagicMock(spec=Event)
    e.id = str(uuid4())
    e.estatus = estatus
    e.deleted_at = "2024-01-01" if deleted else None
    return e


def _service_with_repo(list_public_return=None, get_public_return=None) -> EventService:
    session = AsyncMock()
    svc = EventService(session)
    svc.repo = AsyncMock()
    svc.repo.list_public = AsyncMock(return_value=list_public_return or [])
    svc.repo.get_public = AsyncMock(return_value=get_public_return)
    return svc


@pytest.mark.asyncio
async def test_list_public_events_returns_only_published() -> None:
    published = _make_event(EventStatus.PUBLICADO)
    svc = _service_with_repo(list_public_return=[published])

    result = await svc.list_public_events()

    assert result == [published]
    svc.repo.list_public.assert_awaited_once()


@pytest.mark.asyncio
async def test_list_public_events_empty_when_none_published() -> None:
    svc = _service_with_repo(list_public_return=[])

    result = await svc.list_public_events()

    assert result == []


@pytest.mark.asyncio
async def test_get_public_event_returns_published_event() -> None:
    published = _make_event(EventStatus.PUBLICADO)
    svc = _service_with_repo(get_public_return=published)

    result = await svc.get_public_event_or_404(uuid4())

    assert result is published


@pytest.mark.asyncio
async def test_get_public_event_raises_404_for_borrador() -> None:
    svc = _service_with_repo(get_public_return=None)

    with pytest.raises(DomainError) as exc_info:
        await svc.get_public_event_or_404(uuid4())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_public_event_raises_404_for_cancelado() -> None:
    svc = _service_with_repo(get_public_return=None)

    with pytest.raises(DomainError) as exc_info:
        await svc.get_public_event_or_404(uuid4())

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_public_event_raises_404_for_soft_deleted() -> None:
    svc = _service_with_repo(get_public_return=None)

    with pytest.raises(DomainError) as exc_info:
        await svc.get_public_event_or_404(uuid4())

    assert exc_info.value.status_code == 404

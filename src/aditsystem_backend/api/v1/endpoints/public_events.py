from uuid import UUID

from fastapi import APIRouter

from aditsystem_backend.api.deps import DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.event import EventRead
from aditsystem_backend.services.event import EventService

router = APIRouter(prefix="/public/events", tags=["public-events"])


@router.get("", response_model=list[EventRead])
async def list_public_events(session: DBSession) -> list[EventRead]:
    events = await EventService(session).list_public_events()
    return [EventRead.model_validate(event) for event in events]


@router.get("/{event_id}", response_model=EventRead)
async def get_public_event(event_id: UUID, session: DBSession) -> EventRead:
    try:
        event = await EventService(session).get_public_event_or_404(event_id)
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc

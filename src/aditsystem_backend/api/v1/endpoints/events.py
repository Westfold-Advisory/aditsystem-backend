from uuid import UUID

from fastapi import APIRouter, Request, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.attendance import (
    AttendanceRead,
    GeoCheckinRequest,
    ManualCheckinRequest,
    QRCheckinRequest,
)
from aditsystem_backend.schemas.event import EventCreate, EventQRCodeRead, EventRead, EventUpdate
from aditsystem_backend.schemas.invitation import (
    InvitationCreate,
    InvitationRead,
    InvitationResponseUpdate,
)
from aditsystem_backend.services.event import EventService

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=list[EventRead])
async def list_events(session: DBSession, current_user: CurrentUser) -> list[EventRead]:
    events = await EventService(session).list_events(current_user)
    return [EventRead.model_validate(event) for event in events]


@router.post("", response_model=EventRead, status_code=status.HTTP_201_CREATED)
async def create_event(payload: EventCreate, session: DBSession, current_user: CurrentUser) -> EventRead:
    try:
        event = await EventService(session).create_event(payload=payload, actor=current_user)
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{event_id}", response_model=EventRead)
async def get_event(event_id: UUID, session: DBSession, current_user: CurrentUser) -> EventRead:
    try:
        event = await EventService(session).get_event_for_read(event_id, current_user)
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.patch("/{event_id}", response_model=EventRead)
async def update_event(
    event_id: UUID, payload: EventUpdate, session: DBSession, current_user: CurrentUser
) -> EventRead:
    try:
        event = await EventService(session).update_event(
            event_id=event_id, payload=payload, actor=current_user
        )
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post(
    "/{event_id}/invitations",
    response_model=InvitationRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invitation(
    event_id: UUID, payload: InvitationCreate, session: DBSession, current_user: CurrentUser
) -> InvitationRead:
    try:
        invitation = await EventService(session).create_invitation(
            event_id=event_id, payload=payload, actor=current_user
        )
        return InvitationRead.model_validate(invitation)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/invitations/{invitation_id}/respond", response_model=InvitationRead)
async def respond_invitation(
    event_id: UUID,
    invitation_id: UUID,
    payload: InvitationResponseUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> InvitationRead:
    try:
        invitation = await EventService(session).respond_invitation(
            event_id=event_id,
            invitation_id=invitation_id,
            payload=payload,
            actor=current_user,
        )
        return InvitationRead.model_validate(invitation)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/checkin/qr-token", response_model=EventQRCodeRead)
async def generate_qr(
    event_id: UUID, session: DBSession, current_user: CurrentUser
) -> EventQRCodeRead:
    try:
        return await EventService(session).generate_qr(event_id=event_id, actor=current_user)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/checkin/qr", response_model=AttendanceRead)
async def checkin_qr(
    event_id: UUID,
    payload: QRCheckinRequest,
    request: Request,
    session: DBSession,
    current_user: CurrentUser,
) -> AttendanceRead:
    try:
        attendance = await EventService(session).checkin_with_qr(
            event_id=event_id,
            payload=payload,
            actor=current_user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return AttendanceRead.model_validate(attendance)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/checkin/geolocation", response_model=AttendanceRead)
async def checkin_geolocation(
    event_id: UUID,
    payload: GeoCheckinRequest,
    request: Request,
    session: DBSession,
    current_user: CurrentUser,
) -> AttendanceRead:
    try:
        attendance = await EventService(session).checkin_with_geolocation(
            event_id=event_id,
            payload=payload,
            actor=current_user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return AttendanceRead.model_validate(attendance)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/checkin/manual", response_model=AttendanceRead)
async def manual_checkin(
    event_id: UUID,
    payload: ManualCheckinRequest,
    request: Request,
    session: DBSession,
    current_user: CurrentUser,
) -> AttendanceRead:
    try:
        attendance = await EventService(session).manual_checkin(
            event_id=event_id,
            payload=payload,
            actor=current_user,
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        return AttendanceRead.model_validate(attendance)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{event_id}/attendances", response_model=list[AttendanceRead])
async def list_attendances(
    event_id: UUID, session: DBSession, current_user: CurrentUser
) -> list[AttendanceRead]:
    try:
        attendances = await EventService(session).list_attendances(
            event_id=event_id, actor=current_user
        )
        return [AttendanceRead.model_validate(attendance) for attendance in attendances]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/publish", response_model=EventRead)
async def publish_event(
    event_id: UUID, session: DBSession, current_user: CurrentUser
) -> EventRead:
    try:
        event = await EventService(session).publish_event(event_id=event_id, actor=current_user)
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/unpublish", response_model=EventRead)
async def unpublish_event(
    event_id: UUID, session: DBSession, current_user: CurrentUser
) -> EventRead:
    try:
        event = await EventService(session).unpublish_event(event_id=event_id, actor=current_user)
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/start", response_model=EventRead)
async def start_event(
    event_id: UUID, session: DBSession, current_user: CurrentUser
) -> EventRead:
    try:
        event = await EventService(session).start_event(event_id=event_id, actor=current_user)
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/finish", response_model=EventRead)
async def finish_event(
    event_id: UUID, session: DBSession, current_user: CurrentUser
) -> EventRead:
    try:
        event = await EventService(session).finish_event(event_id=event_id, actor=current_user)
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{event_id}/cancel", response_model=EventRead)
async def cancel_event(
    event_id: UUID, session: DBSession, current_user: CurrentUser
) -> EventRead:
    try:
        event = await EventService(session).cancel_event(event_id=event_id, actor=current_user)
        return EventRead.model_validate(event)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.delete("/{event_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_event(
    event_id: UUID, session: DBSession, current_user: CurrentUser
) -> None:
    try:
        await EventService(session).delete_event(event_id=event_id, actor=current_user)
    except DomainError as exc:
        raise to_http(exc) from exc

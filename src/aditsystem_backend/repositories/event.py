from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.models.event import Event
from aditsystem_backend.models.event_attendance import EventAttendance
from aditsystem_backend.models.event_checkin_token import EventCheckinToken
from aditsystem_backend.models.event_invitation import EventInvitation
from aditsystem_backend.models.enums import EventStatus, InvitationStatus


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, event: Event) -> Event:
        self.session.add(event)
        await self.session.flush()
        await self.session.refresh(event)
        return event

    async def list(self) -> list[Event]:
        result = await self.session.execute(select(Event).order_by(Event.fecha_inicio.asc()))
        return list(result.scalars().all())

    async def list_public(self) -> list[Event]:
        result = await self.session.execute(
            select(Event)
            .where(Event.estatus == EventStatus.PUBLICADO, Event.deleted_at.is_(None))
            .order_by(Event.fecha_inicio.asc())
        )
        return list(result.scalars().all())

    async def get(self, event_id: str) -> Event | None:
        return await self.session.get(Event, event_id)

    async def get_public(self, event_id: str) -> Event | None:
        result = await self.session.execute(
            select(Event).where(
                Event.id == event_id,
                Event.estatus == EventStatus.PUBLICADO,
                Event.deleted_at.is_(None),
            )
        )
        return result.scalar_one_or_none()

    async def accepted_invitation_count(self, event_id: str) -> int:
        result = await self.session.execute(
            select(func.count(EventInvitation.id)).where(
                EventInvitation.evento_id == event_id,
                EventInvitation.estatus == InvitationStatus.ACEPTADA,
            )
        )
        return int(result.scalar_one())

    async def get_invitation(self, event_id: str, invitado_id: str) -> EventInvitation | None:
        result = await self.session.execute(
            select(EventInvitation).where(
                EventInvitation.evento_id == event_id,
                EventInvitation.invitado_id == invitado_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_invitation(self, invitation: EventInvitation) -> EventInvitation:
        self.session.add(invitation)
        await self.session.flush()
        await self.session.refresh(invitation)
        return invitation

    async def get_attendance(self, event_id: str, invitado_id: str) -> EventAttendance | None:
        result = await self.session.execute(
            select(EventAttendance).where(
                EventAttendance.evento_id == event_id,
                EventAttendance.invitado_id == invitado_id,
            )
        )
        return result.scalar_one_or_none()

    async def create_attendance(self, attendance: EventAttendance) -> EventAttendance:
        self.session.add(attendance)
        await self.session.flush()
        await self.session.refresh(attendance)
        return attendance

    async def list_attendances(self, event_id: str) -> list[EventAttendance]:
        result = await self.session.execute(
            select(EventAttendance).where(EventAttendance.evento_id == event_id)
        )
        return list(result.scalars().all())

    async def create_qr_token(self, token: EventCheckinToken) -> EventCheckinToken:
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def get_qr_token_by_jti(self, jti: str) -> EventCheckinToken | None:
        result = await self.session.execute(
            select(EventCheckinToken).where(EventCheckinToken.jti == jti)
        )
        return result.scalar_one_or_none()

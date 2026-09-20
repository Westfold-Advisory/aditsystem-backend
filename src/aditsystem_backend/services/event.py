from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from secrets import token_urlsafe
from uuid import UUID, uuid4

from geoalchemy2.functions import ST_Distance
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.config import get_settings
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.security import (
    create_event_qr_token,
    decode_event_qr_token,
)
from aditsystem_backend.models.enums import (
    EVENT_TRANSITIONS,
    AttendanceStatus,
    CheckinMethod,
    EventStatus,
    InvitationStatus,
    PersonRole,
)
from aditsystem_backend.models.event import Event
from aditsystem_backend.models.event_attendance import EventAttendance
from aditsystem_backend.models.event_checkin_token import EventCheckinToken
from aditsystem_backend.models.event_invitation import EventInvitation
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.persona import Persona
from aditsystem_backend.repositories.event import EventRepository
from aditsystem_backend.schemas.attendance import (
    GeoCheckinRequest,
    ManualCheckinRequest,
    QRCheckinRequest,
)
from aditsystem_backend.schemas.event import EventCreate, EventQRCodeRead, EventUpdate
from aditsystem_backend.schemas.invitation import (
    InvitationCreate,
    InvitationResponseUpdate,
)


class EventService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = EventRepository(session)
        self.settings = get_settings()

    async def create_event(self, *, payload: EventCreate, actor: AuthUser) -> Event:
        if actor.persona.rol not in {
            PersonRole.COORDINADOR_GENERAL,
            PersonRole.COORDINADOR,
            PersonRole.ENLACE,
            PersonRole.ADMIN,
        }:
            raise DomainError("no tienes permisos para crear eventos", status_code=403)
        event = Event(
            created_by_persona_id=actor.persona_id,
            estatus=EventStatus.BORRADOR,
            **payload.model_dump(),
        )
        event.validate_temporal_rules()
        event.sync_geography()
        await self.repo.create(event)
        await self.session.commit()
        return event

    async def list_events(self) -> list[Event]:
        return await self.repo.list()

    async def list_public_events(self) -> list[Event]:
        return await self.repo.list_public()

    async def get_public_event_or_404(self, event_id: UUID) -> Event:
        event = await self.repo.get_public(str(event_id))
        if not event:
            raise DomainError("evento no encontrado", status_code=404)
        return event

    async def get_event_or_404(self, event_id: UUID) -> Event:
        event = await self.repo.get(str(event_id))
        if not event or event.deleted_at is not None:
            raise DomainError("evento no encontrado", status_code=404)
        return event

    async def update_event(
        self, *, event_id: UUID, payload: EventUpdate, actor: AuthUser
    ) -> Event:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)

        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(event, field, value)
        event.validate_temporal_rules()
        if payload.latitud is not None or payload.longitud is not None:
            event.sync_geography()
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def publish_event(self, *, event_id: UUID, actor: AuthUser) -> Event:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        self._apply_transition(event, EventStatus.PUBLICADO)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def unpublish_event(self, *, event_id: UUID, actor: AuthUser) -> Event:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        self._apply_transition(event, EventStatus.BORRADOR)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def start_event(self, *, event_id: UUID, actor: AuthUser) -> Event:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        self._apply_transition(event, EventStatus.EN_CURSO)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def finish_event(self, *, event_id: UUID, actor: AuthUser) -> Event:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        self._apply_transition(event, EventStatus.FINALIZADO)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def cancel_event(self, *, event_id: UUID, actor: AuthUser) -> Event:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        self._apply_transition(event, EventStatus.CANCELADO)
        await self.session.commit()
        await self.session.refresh(event)
        return event

    async def delete_event(self, *, event_id: UUID, actor: AuthUser) -> None:
        """Baja lógica — only allowed for BORRADOR or CANCELADO events."""
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        if event.estatus not in {EventStatus.BORRADOR, EventStatus.CANCELADO}:
            raise DomainError(
                "solo se puede eliminar un evento en estado BORRADOR o CANCELADO",
                status_code=409,
            )
        event.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def create_invitation(
        self, *, event_id: UUID, payload: InvitationCreate, actor: AuthUser
    ) -> EventInvitation:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        self._assert_event_invitable(event)

        persona = await self.session.get(Persona, str(payload.persona_id))
        if not persona or persona.deleted_at is not None:
            raise DomainError("persona no encontrada", status_code=404)

        existing = await self.repo.get_invitation(
            str(event_id), str(payload.persona_id)
        )
        if existing:
            raise DomainError(
                "el invitado ya tiene invitación para este evento", status_code=409
            )

        if event.capacidad_maxima:
            accepted = await self.repo.accepted_invitation_count(str(event_id))
            if accepted >= event.capacidad_maxima:
                raise DomainError("capacidad máxima alcanzada", status_code=409)

        invitation = EventInvitation(
            evento_id=str(event_id),
            persona_id=str(payload.persona_id),
            invitado_por_persona_id=actor.persona_id,
            estatus=InvitationStatus.PENDIENTE,
            codigo_invitacion=token_urlsafe(24),
            fecha_invitacion=datetime.now(UTC),
            observaciones=payload.observaciones,
        )
        await self.repo.create_invitation(invitation)
        attendance = EventAttendance(
            evento_id=str(event_id),
            persona_id=str(payload.persona_id),
            invitacion_id=invitation.id,
            estatus=AttendanceStatus.INVITADO,
        )
        await self.repo.create_attendance(attendance)
        await self.session.commit()
        return invitation

    async def respond_invitation(
        self,
        *,
        event_id: UUID,
        invitation_id: UUID,
        payload: InvitationResponseUpdate,
        actor: AuthUser,
    ) -> EventInvitation:
        invitation = await self.session.get(EventInvitation, str(invitation_id))
        if not invitation or invitation.evento_id != str(event_id):
            raise DomainError("invitación no encontrada", status_code=404)
        if (
            actor.persona.rol != PersonRole.ADMIN
            and actor.persona_id != invitation.persona_id
        ):
            raise DomainError("no puedes responder esta invitación", status_code=403)

        invitation.estatus = payload.estatus
        invitation.fecha_respuesta = datetime.now(UTC)
        invitation.observaciones = payload.observaciones

        attendance = await self.repo.get_attendance(
            str(event_id), invitation.persona_id
        )
        if not attendance:
            raise DomainError("registro de asistencia no encontrado", status_code=404)

        if payload.estatus == InvitationStatus.ACEPTADA:
            attendance.estatus = AttendanceStatus.CONFIRMADO
        elif payload.estatus in {
            InvitationStatus.RECHAZADA,
            InvitationStatus.CANCELADA,
            InvitationStatus.EXPIRADA,
        }:
            attendance.estatus = AttendanceStatus.CANCELADO

        await self.session.commit()
        await self.session.refresh(invitation)
        return invitation

    async def generate_qr(self, *, event_id: UUID, actor: AuthUser) -> EventQRCodeRead:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        self._assert_checkin_allowed_for_event(event)

        token_record = EventCheckinToken(
            event_id=event.id,
            jti=str(uuid4()),
            expires_at=datetime.now(UTC)
            + timedelta(seconds=self.settings.event_qr_ttl_seconds),
            created_by_persona_id=actor.persona_id,
        )
        await self.repo.create_qr_token(token_record)
        token = create_event_qr_token(
            event_id=UUID(event.id),
            jti=UUID(token_record.jti),
            expires_delta=timedelta(seconds=self.settings.event_qr_ttl_seconds),
        )
        await self.session.commit()
        return EventQRCodeRead(
            token=token,
            jti=UUID(token_record.jti),
            event_id=UUID(event.id),
            expires_at=token_record.expires_at,
        )

    async def checkin_with_qr(
        self,
        *,
        event_id: UUID,
        payload: QRCheckinRequest,
        actor: AuthUser,
        ip_address: str | None,
        user_agent: str | None,
    ) -> EventAttendance:
        event = await self.get_event_or_404(event_id)
        invitado_id = self._require_invitado_actor(actor)
        claims = decode_event_qr_token(payload.token)
        if claims["type"] != "event_checkin":
            raise DomainError("token QR inválido", status_code=400)
        if UUID(claims["event_id"]) != event_id:
            raise DomainError("token QR no corresponde al evento", status_code=400)

        qr_record = await self.repo.get_qr_token_by_jti(str(claims["jti"]))
        if not qr_record or qr_record.revoked_at is not None:
            raise DomainError("token QR no activo", status_code=400)
        if qr_record.expires_at <= datetime.now(UTC):
            raise DomainError("token QR expirado", status_code=400)

        return await self._register_checkin(
            event=event,
            invitado_id=invitado_id,
            method=CheckinMethod.QR,
            dispositivo_id=payload.dispositivo_id,
            ip_address=ip_address,
            user_agent=user_agent,
        )

    async def checkin_with_geolocation(
        self,
        *,
        event_id: UUID,
        payload: GeoCheckinRequest,
        actor: AuthUser,
        ip_address: str | None,
        user_agent: str | None,
    ) -> EventAttendance:
        event = await self.get_event_or_404(event_id)
        invitado_id = self._require_invitado_actor(actor)
        if not event.checkin_radio_metros:
            raise DomainError(
                "el evento no tiene radio de check-in configurado", status_code=400
            )
        if payload.precision_metros > self.settings.max_allowed_geo_precision_meters:
            raise DomainError(
                "la precisión del dispositivo es insuficiente", status_code=400
            )

        distance_query = select(
            ST_Distance(
                Event.ubicacion,
                f"SRID=4326;POINT({payload.longitud} {payload.latitud})",
            )
        ).where(Event.id == event.id)
        result = await self.session.execute(distance_query)
        distance = Decimal(str(result.scalar_one() or 0))
        if distance > Decimal(event.checkin_radio_metros):
            raise DomainError(
                "el usuario está fuera del radio permitido", status_code=400
            )

        return await self._register_checkin(
            event=event,
            invitado_id=invitado_id,
            method=CheckinMethod.GEOLOCALIZACION,
            dispositivo_id=payload.dispositivo_id,
            ip_address=ip_address,
            user_agent=user_agent,
            latitud=payload.latitud,
            longitud=payload.longitud,
            distance=distance,
        )

    async def manual_checkin(
        self,
        *,
        event_id: UUID,
        payload: ManualCheckinRequest,
        actor: AuthUser,
        ip_address: str | None,
        user_agent: str | None,
    ) -> EventAttendance:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)

        persona = await self.session.get(Persona, str(payload.persona_id))
        if not persona or persona.deleted_at is not None:
            raise DomainError("persona no encontrada", status_code=404)

        return await self._register_checkin(
            event=event,
            invitado_id=persona.id,
            method=payload.metodo,
            dispositivo_id=payload.dispositivo_id,
            ip_address=ip_address,
            user_agent=user_agent,
            registrado_por=actor.persona_id,
            latitud=payload.latitud,
            longitud=payload.longitud,
        )

    async def list_attendances(
        self, *, event_id: UUID, actor: AuthUser
    ) -> list[EventAttendance]:
        event = await self.get_event_or_404(event_id)
        self._assert_can_manage_event(actor, event)
        return await self.repo.list_attendances(str(event_id))

    def _apply_transition(self, event: Event, target: EventStatus) -> None:
        allowed = EVENT_TRANSITIONS.get(event.estatus, frozenset())
        if target not in allowed:
            raise DomainError(
                f"no se puede pasar de {event.estatus} a {target}",
                status_code=409,
            )
        event.estatus = target

    def _assert_can_manage_event(self, actor: AuthUser, event: Event) -> None:
        if actor.persona.rol == PersonRole.ADMIN:
            return
        if (
            actor.persona.rol
            not in {
                PersonRole.COORDINADOR_GENERAL,
                PersonRole.COORDINADOR,
                PersonRole.ENLACE,
            }
            or event.created_by_persona_id != actor.persona_id
        ):
            raise DomainError("no tienes permisos sobre este evento", status_code=403)

    def _assert_event_invitable(self, event: Event) -> None:
        if event.estatus in {EventStatus.CANCELADO, EventStatus.FINALIZADO}:
            raise DomainError(
                "no se puede invitar usuarios a este evento", status_code=400
            )

    def _assert_checkin_allowed_for_event(self, event: Event) -> None:
        if event.estatus not in {EventStatus.PUBLICADO, EventStatus.EN_CURSO}:
            raise DomainError(
                "el evento no acepta check-ins en su estado actual", status_code=400
            )
        if event.estatus == EventStatus.CANCELADO:
            raise DomainError(
                "un evento cancelado no puede recibir check-ins", status_code=400
            )

    def _assert_checkin_window(self, event: Event) -> None:
        now = datetime.now(UTC)
        if event.checkin_abierto_desde and now < event.checkin_abierto_desde:
            raise DomainError("la ventana de check-in aún no abre", status_code=400)
        if event.checkin_abierto_hasta and now > event.checkin_abierto_hasta:
            raise DomainError("la ventana de check-in ya cerró", status_code=400)

    def _require_invitado_actor(self, actor: AuthUser) -> str:
        if actor.persona.rol != PersonRole.AMIGO:
            raise DomainError(
                "solo una persona AMIGO puede realizar este check-in", status_code=403
            )
        return actor.persona_id

    async def _register_checkin(
        self,
        *,
        event: Event,
        invitado_id: str,
        method: CheckinMethod,
        dispositivo_id: str | None,
        ip_address: str | None,
        user_agent: str | None,
        registrado_por: str | None = None,
        latitud: Decimal | None = None,
        longitud: Decimal | None = None,
        distance: Decimal | None = None,
    ) -> EventAttendance:
        self._assert_checkin_allowed_for_event(event)
        self._assert_checkin_window(event)

        invitation = await self.repo.get_invitation(event.id, invitado_id)
        if not invitation or invitation.estatus != InvitationStatus.ACEPTADA:
            raise DomainError(
                "solo un invitado con invitación aceptada puede realizar check-in",
                status_code=403,
            )

        attendance = await self.repo.get_attendance(event.id, invitado_id)
        if not attendance:
            raise DomainError("registro de asistencia no encontrado", status_code=404)
        if attendance.checkin_at is not None:
            return attendance

        attendance.estatus = AttendanceStatus.PRESENTE
        attendance.checkin_at = datetime.now(UTC)
        attendance.checkin_metodo = method
        attendance.checkin_latitud = latitud
        attendance.checkin_longitud = longitud
        attendance.distancia_evento_metros = distance
        attendance.registrado_por_persona_id = registrado_por
        attendance.dispositivo_id = dispositivo_id
        attendance.ip_address = ip_address
        attendance.user_agent = user_agent
        await self.session.commit()
        await self.session.refresh(attendance)
        return attendance

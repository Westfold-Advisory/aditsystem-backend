from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.documento import Documento
from aditsystem_backend.models.enums import EstatusPersona, PersonRole
from aditsystem_backend.models.event import Event
from aditsystem_backend.models.event_attendance import EventAttendance
from aditsystem_backend.models.event_invitation import EventInvitation
from aditsystem_backend.models.geocerca import Geocerca
from aditsystem_backend.models.persona import Persona
from aditsystem_backend.models.persona_geocerca import PersonaGeocerca
from aditsystem_backend.repositories.persona import PersonaRepository
from aditsystem_backend.repositories.documento import DocumentoRepository
from aditsystem_backend.schemas.documento import PersonaDocumentoCreate
from aditsystem_backend.schemas.geocerca import PersonaGeocercaCreate
from aditsystem_backend.schemas.persona import PersonaCreate, PersonaUpdate
from aditsystem_backend.services.persona_hierarchy import validate_parent
from aditsystem_backend.services.persona_policy import PersonaPolicy


class PersonaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PersonaRepository(session)
        self.policy = PersonaPolicy(session)

    async def create(self, payload: PersonaCreate, actor: AuthUser) -> Persona:
        parent = await self._parent_or_404(payload.parent_persona_id)
        validate_parent(payload.rol, parent)
        await self.policy.assert_create(actor, payload.rol, parent)
        persona = Persona(
            **payload.model_dump(exclude={"parent_persona_id"}),
            parent_persona_id=str(payload.parent_persona_id)
            if payload.parent_persona_id
            else None,
            fecha_registro=datetime.now(UTC),
            estatus=EstatusPersona.ACTIVO,
        )
        await self.repo.create(persona)
        await self.session.commit()
        return persona

    async def get_or_404(self, persona_id: UUID) -> Persona:
        persona = await self.repo.get(str(persona_id))
        if not persona or persona.deleted_at is not None:
            raise DomainError("persona no encontrada", status_code=404)
        return persona

    async def get_authorized(self, persona_id: UUID, actor: AuthUser) -> Persona:
        persona = await self.get_or_404(persona_id)
        await self.policy.assert_manage(actor, persona)
        return persona

    async def children(self, persona_id: UUID, actor: AuthUser) -> list[Persona]:
        persona = await self.get_authorized(persona_id, actor)
        return await self.repo.list_children(persona.id)

    async def descendants(self, persona_id: UUID, actor: AuthUser) -> list[Persona]:
        persona = await self.get_authorized(persona_id, actor)
        if self.policy.is_admin(actor) and persona.id == actor.persona_id:
            return await self.repo.list_global_structure_excluding_admin(actor.persona_id)
        return await self.repo.list_descendants(persona.id)

    @staticmethod
    def _role_counts(descendants: list[Persona]) -> dict[str, int]:
        totals = {
            PersonRole.COORDINADOR: 0,
            PersonRole.ENLACE: 0,
            PersonRole.AMIGO: 0,
        }
        for descendant in descendants:
            if descendant.rol in totals:
                totals[descendant.rol] += 1
        return {
            "coordinadores": totals[PersonRole.COORDINADOR],
            "enlaces": totals[PersonRole.ENLACE],
            "amigos": totals[PersonRole.AMIGO],
        }

    async def metrics(self, persona_id: UUID, actor: AuthUser) -> dict[str, int]:
        from sqlalchemy import func, select

        persona = await self.get_authorized(persona_id, actor)
        descendants = await self.repo.list_descendants(persona.id)

        async def count(model: object, column: object) -> int:
            result = await self.session.execute(
                select(func.count()).select_from(model).where(column == persona.id)
            )
            return int(result.scalar_one())

        return {
            "descendientes": len(descendants),
            **self._role_counts(descendants),
            "documentos": await count(Documento, Documento.persona_id),
            "eventos_creados": await count(Event, Event.created_by_persona_id),
            "invitaciones": await count(EventInvitation, EventInvitation.persona_id),
            "asistencias": await count(EventAttendance, EventAttendance.persona_id),
        }

    async def scoped_map(self, persona_id: UUID, actor: AuthUser) -> dict[str, object]:
        from sqlalchemy import select

        root = await self.get_authorized(persona_id, actor)
        scoped_people = [root, *await self.repo.list_descendants(root.id)]
        persona_ids = [person.id for person in scoped_people]
        geocerca_rows = await self.session.execute(
            select(PersonaGeocerca.persona_id, Geocerca)
            .join(Geocerca, Geocerca.id == PersonaGeocerca.geocerca_id)
            .where(
                PersonaGeocerca.persona_id.in_(persona_ids),
                Geocerca.vigente.is_(True),
            )
            .order_by(PersonaGeocerca.persona_id, Geocerca.tipo, Geocerca.nombre)
        )
        geocercas_by_person: dict[str, list[Geocerca]] = {person_id: [] for person_id in persona_ids}
        for owner_id, geocerca in geocerca_rows.all():
            geocercas_by_person[owner_id].append(geocerca)

        return {
            "root_persona_id": root.id,
            "personas": [
                {
                    "persona_id": person.id,
                    "rol": person.rol,
                    "nombre": person.nombre,
                    "apellido_paterno": person.apellido_paterno,
                    "apellido_materno": person.apellido_materno,
                    "geocercas": geocercas_by_person.get(person.id, []),
                }
                for person in scoped_people
            ],
        }

    async def list_documentos(
        self, persona_id: UUID, actor: AuthUser
    ) -> list[Documento]:
        persona = await self.get_authorized(persona_id, actor)
        return await DocumentoRepository(self.session).list_by_persona(persona.id)

    async def register_documento(
        self, persona_id: UUID, payload: PersonaDocumentoCreate, actor: AuthUser
    ) -> Documento:
        persona = await self.get_authorized(persona_id, actor)
        repo = DocumentoRepository(self.session)
        version = await repo.next_version(persona.id, payload.tipo)
        await repo.retire_previous_versions(persona.id, payload.tipo)
        document = Documento(
            persona_id=persona.id,
            subido_por_persona_id=actor.persona_id,
            version=version,
            is_current=True,
            **payload.model_dump(),
        )
        await repo.create(document)
        await self.session.commit()
        return document

    async def list_geocercas(self, persona_id: UUID, actor: AuthUser) -> list[Geocerca]:
        from sqlalchemy import select

        persona = await self.get_authorized(persona_id, actor)
        result = await self.session.execute(
            select(Geocerca)
            .join(PersonaGeocerca, PersonaGeocerca.geocerca_id == Geocerca.id)
            .where(PersonaGeocerca.persona_id == persona.id, Geocerca.vigente.is_(True))
            .order_by(Geocerca.tipo, Geocerca.nombre)
        )
        return list(result.scalars().all())

    async def assign_geocerca(
        self, persona_id: UUID, payload: PersonaGeocercaCreate, actor: AuthUser
    ) -> Geocerca:
        from sqlalchemy import select

        persona = await self.get_authorized(persona_id, actor)
        geocerca = await self.session.get(Geocerca, str(payload.geocerca_id))
        if not geocerca or not geocerca.vigente:
            raise DomainError("geocerca no encontrada", status_code=404)
        existing = await self.session.execute(
            select(PersonaGeocerca).where(
                PersonaGeocerca.persona_id == persona.id,
                PersonaGeocerca.geocerca_id == geocerca.id,
            )
        )
        if existing.scalar_one_or_none():
            raise DomainError(
                "la geocerca ya está asignada a la persona", status_code=409
            )
        self.session.add(
            PersonaGeocerca(persona_id=persona.id, geocerca_id=geocerca.id)
        )
        await self.session.commit()
        return geocerca

    async def unassign_geocerca(
        self, persona_id: UUID, geocerca_id: UUID, actor: AuthUser
    ) -> None:
        from sqlalchemy import delete

        persona = await self.get_authorized(persona_id, actor)
        result = await self.session.execute(
            delete(PersonaGeocerca).where(
                PersonaGeocerca.persona_id == persona.id,
                PersonaGeocerca.geocerca_id == str(geocerca_id),
            )
        )
        if not result.rowcount:
            raise DomainError("asignación de geocerca no encontrada", status_code=404)
        await self.session.commit()

    async def update(
        self, persona_id: UUID, payload: PersonaUpdate, actor: AuthUser
    ) -> Persona:
        persona = await self.get_authorized(persona_id, actor)
        for field, value in payload.model_dump(exclude_unset=True).items():
            setattr(persona, field, value)
        await self.session.commit()
        await self.session.refresh(persona)
        return persona

    async def soft_delete(self, persona_id: UUID, actor: AuthUser) -> None:
        persona = await self.get_authorized(persona_id, actor)
        if persona.id == actor.persona_id:
            raise DomainError("no puedes darte de baja a ti mismo", status_code=422)
        persona.estatus = EstatusPersona.BAJA
        persona.deleted_at = datetime.now(UTC)
        await self.session.commit()

    async def _parent_or_404(self, parent_id: UUID | None) -> Persona | None:
        if parent_id is None:
            return None
        return await self.get_or_404(parent_id)

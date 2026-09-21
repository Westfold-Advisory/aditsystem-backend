from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.auth_user import AuthUser
from aditsystem_backend.models.documento import Documento
from aditsystem_backend.models.enums import EstatusPersona, NecesidadComunidad, PersonRole
from aditsystem_backend.models.event import Event
from aditsystem_backend.models.event_attendance import EventAttendance
from aditsystem_backend.models.event_invitation import EventInvitation
from aditsystem_backend.models.geocerca import Geocerca
from aditsystem_backend.models.persona import Persona
from aditsystem_backend.models.persona_geocerca import PersonaGeocerca
from aditsystem_backend.models.persona_necesidad_comunidad import PersonaNecesidadComunidad
from aditsystem_backend.repositories.documento import DocumentoRepository
from aditsystem_backend.repositories.persona import PersonaRepository
from aditsystem_backend.schemas.documento import PersonaDocumentoCreate
from aditsystem_backend.schemas.geocerca import PersonaGeocercaCreate
from aditsystem_backend.schemas.persona import PersonaCreate, PersonaUpdate
from aditsystem_backend.services.auth import AuthService
from aditsystem_backend.services.nominatim_geocoding import NominatimGeocodingService, format_persona_address
from aditsystem_backend.services.persona_hierarchy import validate_parent
from aditsystem_backend.services.persona_policy import PersonaPolicy

_ADDRESS_FIELDS = (
    "calle",
    "numero_exterior",
    "numero_interior",
    "colonia",
    "codigo_postal",
    "entre_calles",
)


class PersonaService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.repo = PersonaRepository(session)
        self.policy = PersonaPolicy(session)
        self.geocoder = NominatimGeocodingService()

    async def create(self, payload: PersonaCreate, actor: AuthUser) -> Persona:
        parent = await self._parent_or_404(payload.parent_persona_id)
        validate_parent(payload.rol, parent)
        await self.policy.assert_create(actor, payload.rol, parent)
        data = payload.model_dump(
            exclude={"parent_persona_id", "necesidades_comunidad", "email", "password"}
        )
        latitud, longitud = await self._resolve_coordinates(payload)
        if latitud is not None and longitud is not None:
            data["latitud"] = latitud
            data["longitud"] = longitud
        persona = Persona(
            **data,
            parent_persona_id=str(payload.parent_persona_id) if payload.parent_persona_id else None,
            fecha_registro=datetime.now(UTC),
            estatus=EstatusPersona.ACTIVO,
        )
        await self.repo.create(persona)
        await self._replace_necesidades(persona, payload.necesidades_comunidad)
        if payload.email is not None and payload.password is not None:
            await AuthService(self.session).attach_credentials(
                persona,
                str(payload.email),
                payload.password,
                actor,
                commit=False,
            )
        await self.session.commit()
        refreshed = await self.repo.get(persona.id)
        if refreshed is None:
            raise DomainError("persona no encontrada tras crear", status_code=500)
        return refreshed

    async def change_password(self, persona_id: UUID, new_password: str, actor: AuthUser) -> None:
        await self.get_authorized(persona_id, actor)
        await AuthService(self.session).set_password(str(persona_id), new_password, actor)

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
                    "latitud": person.latitud,
                    "longitud": person.longitud,
                    "geocercas": geocercas_by_person.get(person.id, []),
                }
                for person in scoped_people
            ],
        }

    async def scoped_coverage_map(
        self,
        persona_id: UUID,
        actor: AuthUser,
        *,
        grid_precision: int = 3,
        necesidad: NecesidadComunidad | None = None,
    ) -> dict[str, object]:
        from decimal import ROUND_HALF_UP

        from sqlalchemy import func, select

        root = await self.get_authorized(persona_id, actor)
        scoped_people = [root, *await self.repo.list_descendants(root.id)]
        persona_ids = [person.id for person in scoped_people]

        pines = [
            {
                "persona_id": person.id,
                "rol": person.rol,
                "nombre": person.nombre,
                "apellido_paterno": person.apellido_paterno,
                "apellido_materno": person.apellido_materno,
                "latitud": person.latitud,
                "longitud": person.longitud,
            }
            for person in scoped_people
            if person.latitud is not None and person.longitud is not None and person.deleted_at is None
        ]

        quant = Decimal("1").scaleb(-grid_precision)
        lat_bucket = func.round(Persona.latitud, grid_precision)
        lng_bucket = func.round(Persona.longitud, grid_precision)
        stmt = (
            select(
                lat_bucket.label("latitud"),
                lng_bucket.label("longitud"),
                PersonaNecesidadComunidad.necesidad,
                func.count().label("intensidad"),
            )
            .select_from(PersonaNecesidadComunidad)
            .join(Persona, Persona.id == PersonaNecesidadComunidad.persona_id)
            .where(
                PersonaNecesidadComunidad.persona_id.in_(persona_ids),
                Persona.deleted_at.is_(None),
                Persona.latitud.is_not(None),
                Persona.longitud.is_not(None),
            )
            .group_by(lat_bucket, lng_bucket, PersonaNecesidadComunidad.necesidad)
        )
        if necesidad is not None:
            stmt = stmt.where(PersonaNecesidadComunidad.necesidad == necesidad)

        heatmap_rows = await self.session.execute(stmt)
        heatmap = [
            {
                "latitud": Decimal(str(row.latitud)).quantize(quant, rounding=ROUND_HALF_UP),
                "longitud": Decimal(str(row.longitud)).quantize(quant, rounding=ROUND_HALF_UP),
                "necesidad": row.necesidad,
                "intensidad": int(row.intensidad),
            }
            for row in heatmap_rows.all()
        ]

        return {
            "root_persona_id": root.id,
            "pines": pines,
            "heatmap": heatmap,
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
        updates = payload.model_dump(exclude_unset=True)
        necesidades = updates.pop("necesidades_comunidad", None)

        coords_in_payload = "latitud" in payload.model_fields_set or "longitud" in payload.model_fields_set
        address_touched = any(field in payload.model_fields_set for field in _ADDRESS_FIELDS)
        if not coords_in_payload and address_touched:
            latitud, longitud = await self._resolve_coordinates(payload, persona=persona)
            if latitud is not None and longitud is not None:
                updates["latitud"] = latitud
                updates["longitud"] = longitud

        for field, value in updates.items():
            setattr(persona, field, value)
        if "necesidades_comunidad" in payload.model_fields_set:
            await self._replace_necesidades(persona, necesidades)
        await self.session.commit()
        refreshed = await self.repo.get(persona.id)
        if refreshed is None:
            raise DomainError("persona no encontrada tras actualizar", status_code=500)
        return refreshed

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

    async def _replace_necesidades(
        self,
        persona: Persona,
        necesidades: list[NecesidadComunidad] | None,
    ) -> None:
        from sqlalchemy import delete

        if necesidades is None:
            return
        await self.session.execute(
            delete(PersonaNecesidadComunidad).where(
                PersonaNecesidadComunidad.persona_id == persona.id
            )
        )
        for necesidad in necesidades:
            self.session.add(
                PersonaNecesidadComunidad(persona_id=persona.id, necesidad=necesidad)
            )

    async def _resolve_coordinates(
        self,
        payload: PersonaCreate | PersonaUpdate,
        *,
        persona: Persona | None = None,
    ) -> tuple[Decimal | None, Decimal | None]:
        latitud = getattr(payload, "latitud", None)
        longitud = getattr(payload, "longitud", None)
        if latitud is not None and longitud is not None:
            return latitud, longitud

        def pick(field: str) -> str | None:
            value = getattr(payload, field, None)
            if value is not None:
                return value
            return getattr(persona, field, None) if persona is not None else None

        address = format_persona_address(
            calle=pick("calle"),
            numero_exterior=pick("numero_exterior"),
            colonia=pick("colonia"),
            codigo_postal=pick("codigo_postal"),
            entre_calles=pick("entre_calles"),
        )
        if address is None or not self.geocoder.enabled:
            return None, None
        return await self.geocoder.geocode(address)

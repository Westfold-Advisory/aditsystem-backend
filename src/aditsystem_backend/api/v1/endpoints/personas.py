from uuid import UUID

from fastapi import APIRouter, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.persona import PersonaCreate, PersonaRead, PersonaUpdate
from aditsystem_backend.services.persona import PersonaService

router = APIRouter(prefix="/personas", tags=["personas"])


@router.post("", response_model=PersonaRead, status_code=status.HTTP_201_CREATED)
async def create_persona(payload: PersonaCreate, session: DBSession, current_user: CurrentUser) -> PersonaRead:
    try:
        return PersonaRead.model_validate(await PersonaService(session).create(payload, current_user))
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{persona_id}", response_model=PersonaRead)
async def get_persona(persona_id: UUID, session: DBSession, current_user: CurrentUser) -> PersonaRead:
    try:
        return PersonaRead.model_validate(await PersonaService(session).get_authorized(persona_id, current_user))
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{persona_id}/descendientes", response_model=list[PersonaRead])
async def list_descendants(persona_id: UUID, session: DBSession, current_user: CurrentUser) -> list[PersonaRead]:
    try:
        personas = await PersonaService(session).children(persona_id, current_user)
        return [PersonaRead.model_validate(persona) for persona in personas]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.patch("/{persona_id}", response_model=PersonaRead)
async def update_persona(persona_id: UUID, payload: PersonaUpdate, session: DBSession, current_user: CurrentUser) -> PersonaRead:
    try:
        return PersonaRead.model_validate(await PersonaService(session).update(persona_id, payload, current_user))
    except DomainError as exc:
        raise to_http(exc) from exc


@router.delete("/{persona_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_persona(persona_id: UUID, session: DBSession, current_user: CurrentUser) -> None:
    try:
        await PersonaService(session).soft_delete(persona_id, current_user)
    except DomainError as exc:
        raise to_http(exc) from exc

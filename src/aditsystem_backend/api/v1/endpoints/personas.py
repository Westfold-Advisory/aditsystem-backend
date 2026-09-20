from uuid import UUID

from fastapi import APIRouter, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.persona import PersonaCreate, PersonaMetricas, PersonaRead, PersonaUpdate
from aditsystem_backend.schemas.documento import DocumentoList, DocumentoRead, PersonaDocumentoCreate
from aditsystem_backend.schemas.geocerca import GeocercaRead, PersonaGeocercaCreate
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
        personas = await PersonaService(session).descendants(persona_id, current_user)
        return [PersonaRead.model_validate(persona) for persona in personas]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{persona_id}/metricas", response_model=PersonaMetricas)
async def get_metrics(persona_id: UUID, session: DBSession, current_user: CurrentUser) -> PersonaMetricas:
    try:
        return PersonaMetricas.model_validate(await PersonaService(session).metrics(persona_id, current_user))
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{persona_id}/documentos", response_model=list[DocumentoList])
async def list_documentos(persona_id: UUID, session: DBSession, current_user: CurrentUser) -> list[DocumentoList]:
    try:
        documents = await PersonaService(session).list_documentos(persona_id, current_user)
        return [DocumentoList.model_validate(document) for document in documents]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{persona_id}/documentos", response_model=DocumentoRead, status_code=status.HTTP_201_CREATED)
async def register_documento(persona_id: UUID, payload: PersonaDocumentoCreate, session: DBSession, current_user: CurrentUser) -> DocumentoRead:
    try:
        document = await PersonaService(session).register_documento(persona_id, payload, current_user)
        return DocumentoRead.model_validate(document)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{persona_id}/geocercas", response_model=list[GeocercaRead])
async def list_geocercas(persona_id: UUID, session: DBSession, current_user: CurrentUser) -> list[GeocercaRead]:
    try:
        geocercas = await PersonaService(session).list_geocercas(persona_id, current_user)
        return [GeocercaRead.model_validate(item) for item in geocercas]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("/{persona_id}/geocercas", response_model=GeocercaRead, status_code=status.HTTP_201_CREATED)
async def assign_geocerca(persona_id: UUID, payload: PersonaGeocercaCreate, session: DBSession, current_user: CurrentUser) -> GeocercaRead:
    try:
        return GeocercaRead.model_validate(await PersonaService(session).assign_geocerca(persona_id, payload, current_user))
    except DomainError as exc:
        raise to_http(exc) from exc


@router.delete("/{persona_id}/geocercas/{geocerca_id}", status_code=status.HTTP_204_NO_CONTENT)
async def unassign_geocerca(persona_id: UUID, geocerca_id: UUID, session: DBSession, current_user: CurrentUser) -> None:
    try:
        await PersonaService(session).unassign_geocerca(persona_id, geocerca_id, current_user)
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

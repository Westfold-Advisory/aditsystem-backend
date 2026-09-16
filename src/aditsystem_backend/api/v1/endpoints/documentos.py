from uuid import UUID

from fastapi import APIRouter, Query, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.models.enums import DocumentoTipo, EntityType
from aditsystem_backend.schemas.documento import (
    DocumentoCreate,
    DocumentoList,
    DocumentoRead,
)
from aditsystem_backend.services.documento import DocumentoService

router = APIRouter(prefix="/documentos", tags=["documentos"])


@router.get("", response_model=list[DocumentoList])
async def list_documentos(
    session: DBSession,
    current_user: CurrentUser,
    entity_type: EntityType = Query(...),
    entity_id: UUID = Query(...),
    tipo: DocumentoTipo | None = Query(default=None),
) -> list[DocumentoList]:
    try:
        docs = await DocumentoService(session).list_documentos(
            entity_type=entity_type,
            entity_id=entity_id,
            tipo=tipo,
            actor=current_user,
        )
        return [DocumentoList.model_validate(d) for d in docs]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("", response_model=DocumentoRead, status_code=status.HTTP_201_CREATED)
async def register_documento(
    payload: DocumentoCreate, session: DBSession, current_user: CurrentUser
) -> DocumentoRead:
    try:
        doc = await DocumentoService(session).register_documento(
            payload=payload, actor=current_user
        )
        return DocumentoRead.model_validate(doc)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{documento_id}", response_model=DocumentoRead)
async def get_documento(
    documento_id: UUID, session: DBSession, current_user: CurrentUser
) -> DocumentoRead:
    try:
        doc = await DocumentoService(session).get_documento_or_404(documento_id, current_user)
        return DocumentoRead.model_validate(doc)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.delete("/{documento_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_documento(
    documento_id: UUID, session: DBSession, current_user: CurrentUser
) -> None:
    try:
        await DocumentoService(session).soft_delete(
            documento_id=documento_id, actor=current_user
        )
    except DomainError as exc:
        raise to_http(exc) from exc

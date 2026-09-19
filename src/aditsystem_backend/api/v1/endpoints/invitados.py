from uuid import UUID

from fastapi import APIRouter, Query, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.invitado import (
    InvitadoCreate,
    InvitadoList,
    InvitadoRead,
    InvitadoUpdate,
)
from aditsystem_backend.services.invitado import InvitadoService

router = APIRouter(prefix="/invitados", tags=["invitados"])


@router.get("", response_model=list[InvitadoList])
async def list_invitados(
    session: DBSession,
    current_user: CurrentUser,
    lider_id: UUID | None = Query(default=None),
) -> list[InvitadoList]:
    try:
        invitados = await InvitadoService(session).list_invitados(current_user, lider_id)
        return [InvitadoList.model_validate(i) for i in invitados]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("", response_model=InvitadoRead, status_code=status.HTTP_201_CREATED)
async def create_invitado(
    payload: InvitadoCreate, session: DBSession, current_user: CurrentUser
) -> InvitadoRead:
    try:
        invitado = await InvitadoService(session).create_invitado(
            payload=payload, actor=current_user
        )
        return InvitadoRead.model_validate(invitado)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{invitado_id}", response_model=InvitadoRead)
async def get_invitado(
    invitado_id: UUID, session: DBSession, current_user: CurrentUser
) -> InvitadoRead:
    try:
        invitado = await InvitadoService(session).get_invitado_or_404(invitado_id, current_user)
        return InvitadoRead.model_validate(invitado)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.patch("/{invitado_id}", response_model=InvitadoRead)
async def update_invitado(
    invitado_id: UUID,
    payload: InvitadoUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> InvitadoRead:
    try:
        invitado = await InvitadoService(session).update_invitado(
            invitado_id=invitado_id, payload=payload, actor=current_user
        )
        return InvitadoRead.model_validate(invitado)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.delete("/{invitado_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invitado(
    invitado_id: UUID, session: DBSession, current_user: CurrentUser
) -> None:
    try:
        await InvitadoService(session).soft_delete(
            invitado_id=invitado_id, actor=current_user
        )
    except DomainError as exc:
        raise to_http(exc) from exc

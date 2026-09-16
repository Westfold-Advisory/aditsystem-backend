from uuid import UUID

from fastapi import APIRouter, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.politico import (
    PoliticoCreate,
    PoliticoList,
    PoliticoRead,
    PoliticoUpdate,
)
from aditsystem_backend.services.politico import PoliticoService

router = APIRouter(prefix="/politicos", tags=["politicos"])


@router.get("", response_model=list[PoliticoList])
async def list_politicos(session: DBSession, current_user: CurrentUser) -> list[PoliticoList]:
    try:
        politicos = await PoliticoService(session).list_politicos(current_user)
        return [PoliticoList.model_validate(p) for p in politicos]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("", response_model=PoliticoRead, status_code=status.HTTP_201_CREATED)
async def create_politico(
    payload: PoliticoCreate, session: DBSession, current_user: CurrentUser
) -> PoliticoRead:
    try:
        politico = await PoliticoService(session).create_politico(
            payload=payload, actor=current_user
        )
        return PoliticoRead.model_validate(politico)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{politico_id}", response_model=PoliticoRead)
async def get_politico(
    politico_id: UUID, session: DBSession, current_user: CurrentUser
) -> PoliticoRead:
    try:
        politico = await PoliticoService(session).get_politico_or_404(politico_id)
        return PoliticoRead.model_validate(politico)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.patch("/{politico_id}", response_model=PoliticoRead)
async def update_politico(
    politico_id: UUID,
    payload: PoliticoUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> PoliticoRead:
    try:
        politico = await PoliticoService(session).update_politico(
            politico_id=politico_id, payload=payload, actor=current_user
        )
        return PoliticoRead.model_validate(politico)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.delete("/{politico_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_politico(
    politico_id: UUID, session: DBSession, current_user: CurrentUser
) -> None:
    try:
        await PoliticoService(session).soft_delete(
            politico_id=politico_id, actor=current_user
        )
    except DomainError as exc:
        raise to_http(exc) from exc

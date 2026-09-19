from uuid import UUID

from fastapi import APIRouter, Query, status

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.core.exceptions import to_http_exception as to_http
from aditsystem_backend.schemas.lider import (
    LiderCreate,
    LiderList,
    LiderRead,
    LiderUpdate,
)
from aditsystem_backend.services.lider import LiderService

router = APIRouter(prefix="/lideres", tags=["lideres"])


@router.get("", response_model=list[LiderList])
async def list_lideres(
    session: DBSession,
    current_user: CurrentUser,
    politico_id: UUID | None = Query(default=None),
) -> list[LiderList]:
    try:
        lideres = await LiderService(session).list_lideres(current_user, politico_id)
        return [LiderList.model_validate(lider) for lider in lideres]
    except DomainError as exc:
        raise to_http(exc) from exc


@router.post("", response_model=LiderRead, status_code=status.HTTP_201_CREATED)
async def create_lider(
    payload: LiderCreate, session: DBSession, current_user: CurrentUser
) -> LiderRead:
    try:
        lider = await LiderService(session).create_lider(payload=payload, actor=current_user)
        return LiderRead.model_validate(lider)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.get("/{lider_id}", response_model=LiderRead)
async def get_lider(
    lider_id: UUID, session: DBSession, current_user: CurrentUser
) -> LiderRead:
    try:
        lider = await LiderService(session).get_lider_or_404(lider_id, current_user)
        return LiderRead.model_validate(lider)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.patch("/{lider_id}", response_model=LiderRead)
async def update_lider(
    lider_id: UUID,
    payload: LiderUpdate,
    session: DBSession,
    current_user: CurrentUser,
) -> LiderRead:
    try:
        lider = await LiderService(session).update_lider(
            lider_id=lider_id, payload=payload, actor=current_user
        )
        return LiderRead.model_validate(lider)
    except DomainError as exc:
        raise to_http(exc) from exc


@router.delete("/{lider_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_lider(
    lider_id: UUID, session: DBSession, current_user: CurrentUser
) -> None:
    try:
        await LiderService(session).soft_delete(lider_id=lider_id, actor=current_user)
    except DomainError as exc:
        raise to_http(exc) from exc

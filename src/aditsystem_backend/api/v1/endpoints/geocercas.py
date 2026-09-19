from fastapi import APIRouter, Query

from aditsystem_backend.api.deps import CurrentUser, DBSession
from aditsystem_backend.models.enums import TipoGeocerca
from aditsystem_backend.schemas.geocerca import (
    ContainsPointRequest,
    GeocercaCreate,
    GeocercaListParams,
    GeocercaRead,
    GeocercaSimplified,
    GeocercaWithGeometry,
)
from aditsystem_backend.services.geocerca import GeocercaService

router = APIRouter(prefix="/geocercas", tags=["geocercas"])


@router.get("", response_model=list[GeocercaSimplified])
async def list_geocercas(
    session: DBSession,
    tipo: TipoGeocerca | None = Query(default=None),
    codigo: str | None = Query(default=None),
    codigo_padre: str | None = Query(default=None),
    vigente: bool = Query(default=True),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
) -> list[GeocercaSimplified]:
    params = GeocercaListParams(
        tipo=tipo,
        codigo=codigo,
        codigo_padre=codigo_padre,
        vigente=vigente,
        page=page,
        page_size=page_size,
    )
    return await GeocercaService(session).list(params)


@router.get("/contains", response_model=list[GeocercaWithGeometry])
async def geocercas_containing_point(
    session: DBSession,
    latitud: float = Query(ge=-90, le=90),
    longitud: float = Query(ge=-180, le=180),
    tipo: TipoGeocerca | None = Query(default=None),
) -> list[GeocercaWithGeometry]:
    """Return all active geocercas whose boundary contains the given point."""
    req = ContainsPointRequest(latitud=latitud, longitud=longitud, tipo=tipo)
    return await GeocercaService(session).contains_point(req)


@router.get("/{geocerca_id}", response_model=GeocercaWithGeometry)
async def get_geocerca(
    geocerca_id: str,
    session: DBSession,
) -> GeocercaWithGeometry:
    return await GeocercaService(session).get_detail(geocerca_id)


@router.post("", response_model=GeocercaRead, status_code=201)
async def create_geocerca(
    payload: GeocercaCreate,
    session: DBSession,
    _current_user: CurrentUser,
) -> GeocercaRead:
    return await GeocercaService(session).create(payload)


@router.delete("/{geocerca_id}", response_model=GeocercaRead)
async def deactivate_geocerca(
    geocerca_id: str,
    session: DBSession,
    _current_user: CurrentUser,
) -> GeocercaRead:
    """Mark a geocerca as no longer vigente (logical deactivation)."""
    return await GeocercaService(session).deactivate(geocerca_id)

"""HTTP integration tests for geocerca catalog geometry serialization."""

from __future__ import annotations

from uuid import uuid4

import helpers
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncEngine, async_sessionmaker

from aditsystem_backend.models.enums import TipoGeocerca
from aditsystem_backend.repositories.geocerca import GeocercaRepository
from aditsystem_backend.schemas.geocerca import GeocercaCreate
from aditsystem_backend.services.geocerca import GeocercaService, _hash_geometry

API = f"{helpers.API_PREFIX}/geocercas"

# INE Puebla sección 1103: ST_Simplify(..., 0.001) collapses to empty geometry.
_REGRESSION_POLYGON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-98.21867563920583, 19.053629849451685],
            [-98.217075369, 19.052814085],
            [-98.215548185, 19.052035557],
            [-98.213952781, 19.051222231],
            [-98.2137095, 19.051098206],
            [-98.213384269, 19.050932402],
            [-98.212445472, 19.050453795],
            [-98.210814967, 19.04962253],
            [-98.209326602, 19.048863697],
            [-98.20780687, 19.048088887],
            [-98.208223934, 19.047312726],
            [-98.209772992, 19.048097076],
            [-98.211260914, 19.048850448],
            [-98.212881004, 19.049672307],
            [-98.214434545, 19.050460386],
            [-98.215987528, 19.051242913],
            [-98.21751431, 19.052022049],
            [-98.218377705, 19.05245967],
            [-98.2191293103061, 19.052829638663084],
            [-98.21867563920583, 19.053629849451685],
        ]
    ],
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simplified_geometry_falls_back_when_simplify_collapses(
    integration_client: AsyncClient,
    integration_auth_engine: AsyncEngine,
) -> None:
    """Regression for TRA-131: empty ST_Simplify must not break list serialization."""
    session_factory = async_sessionmaker(
        integration_auth_engine, expire_on_commit=False
    )
    suffix = uuid4().hex[:8]
    codigo = f"tra131-{suffix}"
    geocerca_id: str

    async with session_factory() as session:
        repo = GeocercaRepository(session)
        existing = await repo.get_by_hash(
            _hash_geometry(_REGRESSION_POLYGON), TipoGeocerca.SECCION
        )
        if existing is None:
            created = await GeocercaService(session).create(
                GeocercaCreate(
                    tipo=TipoGeocerca.SECCION,
                    nombre=f"Sección TRA-131 {suffix}",
                    codigo=codigo,
                    codigo_padre="115",
                    fuente="pytest-tra-131",
                    geojson_geometry=_REGRESSION_POLYGON,
                )
            )
            geocerca_id = created.id
        else:
            geocerca_id = existing.id

        simplified = await repo.get_simplified_geometry_geojson(geocerca_id)

    assert simplified is not None
    assert simplified["type"] == "Polygon"
    assert simplified["coordinates"]

    for page in (1, 2, 3):
        response = await integration_client.get(
            f"{API}?tipo=SECCION&page={page}&page_size=50"
        )
        assert response.status_code == 200, response.text

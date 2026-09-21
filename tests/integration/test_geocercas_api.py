"""HTTP integration tests for the /api/v1/geocercas catalog resource."""

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
from helpers import SEED_ENLACE_EMAIL, bearer, login

API = f"{helpers.API_PREFIX}/geocercas"


def _square_polygon(codigo: str) -> dict[str, object]:
    """Small, near-unique bbox so geometry hash does not collide across runs."""
    bump = (hash(codigo) % 1000) / 100_000
    return {
        "type": "Polygon",
        "coordinates": [
            [
                [-97.0 + bump, 20.0],
                [-96.9 + bump, 20.0],
                [-96.9 + bump, 20.1],
                [-97.0 + bump, 20.1],
                [-97.0 + bump, 20.0],
            ]
        ],
    }


def _geocerca_payload(codigo: str, **overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "tipo": "MUNICIPIO",
        "nombre": f"Municipio integracion {codigo}",
        "codigo": codigo,
        "fuente": "pytest-integration",
        "geojson_geometry": _square_polygon(codigo),
    }
    payload.update(overrides)
    return payload


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_geocerca_requires_authentication(
    integration_client: AsyncClient,
) -> None:
    codigo = f"geo-anon-{uuid4().hex[:8]}"
    response = await integration_client.post(API, json=_geocerca_payload(codigo))
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_get_list_and_deactivate_geocerca(
    integration_client: AsyncClient,
) -> None:
    token = await login(integration_client, SEED_ENLACE_EMAIL)
    codigo = f"geo-lifecycle-{uuid4().hex[:8]}"

    create = await integration_client.post(
        API, json=_geocerca_payload(codigo), headers=bearer(token)
    )
    assert create.status_code == 201, create.text
    geocerca_id = create.json()["id"]
    assert create.json()["vigente"] is True

    detail = await integration_client.get(f"{API}/{geocerca_id}")
    assert detail.status_code == 200, detail.text
    assert detail.json()["id"] == geocerca_id
    assert detail.json()["geometry"]["type"] == "Polygon"

    listed = await integration_client.get(f"{API}?codigo={codigo}")
    assert listed.status_code == 200, listed.text
    items = listed.json()
    assert len(items) == 1
    assert items[0]["id"] == geocerca_id
    assert items[0]["geometry_simplified"] is not None

    deactivate = await integration_client.delete(
        f"{API}/{geocerca_id}", headers=bearer(token)
    )
    assert deactivate.status_code == 200, deactivate.text
    assert deactivate.json()["vigente"] is False

    listed_active_only = await integration_client.get(f"{API}?codigo={codigo}")
    assert listed_active_only.json() == []

    listed_inactive = await integration_client.get(f"{API}?codigo={codigo}&vigente=false")
    assert len(listed_inactive.json()) == 1
    assert listed_inactive.json()[0]["id"] == geocerca_id

    second_deactivate = await integration_client.delete(
        f"{API}/{geocerca_id}", headers=bearer(token)
    )
    assert second_deactivate.status_code == 400


@pytest.mark.integration
@pytest.mark.asyncio
async def test_delete_geocerca_requires_authentication(
    integration_client: AsyncClient,
) -> None:
    geocerca_id = await helpers.create_integration_geocerca(f"geo-del-anon-{uuid4().hex[:8]}")
    response = await integration_client.delete(f"{API}/{geocerca_id}")
    assert response.status_code == 401


@pytest.mark.integration
@pytest.mark.asyncio
async def test_get_geocerca_not_found(integration_client: AsyncClient) -> None:
    response = await integration_client.get(f"{API}/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_geocerca_duplicate_geometry_conflicts(
    integration_client: AsyncClient,
) -> None:
    token = await login(integration_client, SEED_ENLACE_EMAIL)
    codigo = f"geo-dup-{uuid4().hex[:8]}"

    first = await integration_client.post(
        API, json=_geocerca_payload(codigo), headers=bearer(token)
    )
    assert first.status_code == 201, first.text

    second = await integration_client.post(
        API,
        json=_geocerca_payload(f"{codigo}-other-codigo", geojson_geometry=_square_polygon(codigo)),
        headers=bearer(token),
    )
    assert second.status_code == 409


@pytest.mark.integration
@pytest.mark.asyncio
async def test_geocercas_containing_point(integration_client: AsyncClient) -> None:
    token = await login(integration_client, SEED_ENLACE_EMAIL)
    codigo = f"geo-contains-{uuid4().hex[:8]}"

    create = await integration_client.post(
        API, json=_geocerca_payload(codigo), headers=bearer(token)
    )
    assert create.status_code == 201, create.text
    geocerca_id = create.json()["id"]

    inside = await integration_client.get(
        f"{API}/contains", params={"latitud": 20.05, "longitud": -96.95}
    )
    assert inside.status_code == 200, inside.text
    assert any(item["id"] == geocerca_id for item in inside.json())
    matched = next(item for item in inside.json() if item["id"] == geocerca_id)
    assert matched["geometry"]["type"] == "Polygon"

    outside = await integration_client.get(
        f"{API}/contains", params={"latitud": -10.0, "longitud": 40.0}
    )
    assert outside.status_code == 200
    assert all(item["id"] != geocerca_id for item in outside.json())

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

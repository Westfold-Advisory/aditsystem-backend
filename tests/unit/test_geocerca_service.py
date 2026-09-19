"""Unit tests for GeocercaService business logic (mocked DB)."""

from datetime import UTC, datetime
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import TipoGeocerca
from aditsystem_backend.models.geocerca import Geocerca
from aditsystem_backend.schemas.geocerca import GeocercaCreate
from aditsystem_backend.services.geocerca import GeocercaService, _hash_geometry


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_POLYGON_GEOJSON = {
    "type": "Polygon",
    "coordinates": [
        [
            [-99.09, 19.50],
            [-99.06, 19.49],
            [-99.05, 19.42],
            [-99.12, 19.40],
            [-99.09, 19.50],
        ]
    ],
}


def _make_geocerca(
    tipo: TipoGeocerca = TipoGeocerca.ESTADO,
    vigente: bool = True,
) -> Geocerca:
    g = MagicMock(spec=Geocerca)
    g.id = str(uuid4())
    g.tipo = tipo
    g.nombre = "Test Geocerca"
    g.codigo = "9"
    g.codigo_padre = None
    g.fuente = "test.geojson"
    g.hash_geometria = _hash_geometry(_POLYGON_GEOJSON)
    g.version = 1
    g.vigente = vigente
    g.importado_en = datetime.now(UTC)
    g.importado_por = None
    g.created_at = datetime.now(UTC)
    g.updated_at = datetime.now(UTC)
    return g


def _service_with_mocked_repo(
    repo_get: Geocerca | None = None,
    repo_get_by_hash: Geocerca | None = None,
) -> GeocercaService:
    session = AsyncMock()
    session.commit = AsyncMock()
    session.refresh = AsyncMock()

    svc = GeocercaService(session)
    svc.repo = AsyncMock()
    svc.repo.get = AsyncMock(return_value=repo_get)
    svc.repo.get_by_hash = AsyncMock(return_value=repo_get_by_hash)
    svc.repo.create = AsyncMock(side_effect=lambda g: g)
    svc.repo.save = AsyncMock(side_effect=lambda g: g)
    svc.repo.get_geometry_geojson = AsyncMock(return_value=_POLYGON_GEOJSON)
    svc.repo.get_simplified_geometry_geojson = AsyncMock(return_value=_POLYGON_GEOJSON)
    svc.repo.contains_point = AsyncMock(return_value=[])
    return svc


# ---------------------------------------------------------------------------
# _hash_geometry
# ---------------------------------------------------------------------------

class TestHashGeometry:
    def test_deterministic(self) -> None:
        h1 = _hash_geometry(_POLYGON_GEOJSON)
        h2 = _hash_geometry(_POLYGON_GEOJSON)
        assert h1 == h2

    def test_different_geometries_produce_different_hashes(self) -> None:
        other = {
            "type": "Polygon",
            "coordinates": [
                [[-98.0, 19.0], [-98.5, 19.5], [-97.5, 19.5], [-98.0, 19.0]]
            ],
        }
        assert _hash_geometry(_POLYGON_GEOJSON) != _hash_geometry(other)

    def test_length_is_64_chars(self) -> None:
        h = _hash_geometry(_POLYGON_GEOJSON)
        assert len(h) == 64


# ---------------------------------------------------------------------------
# GeocercaService.create
# ---------------------------------------------------------------------------

class TestGeocercaServiceCreate:
    @pytest.mark.asyncio
    async def test_raises_conflict_when_duplicate(self) -> None:
        existing = _make_geocerca()
        svc = _service_with_mocked_repo(repo_get_by_hash=existing)

        payload = GeocercaCreate(
            tipo=TipoGeocerca.ESTADO,
            nombre="DF",
            codigo="9",
            fuente="states.geojson",
            geojson_geometry=_POLYGON_GEOJSON,
        )

        with pytest.raises(DomainError) as exc_info:
            await svc.create(payload)
        assert exc_info.value.status_code == 409

    @pytest.mark.asyncio
    async def test_creates_new_geocerca(self) -> None:
        svc = _service_with_mocked_repo(repo_get_by_hash=None)
        new_geocerca = _make_geocerca()
        svc.repo.create = AsyncMock(return_value=new_geocerca)

        # session.refresh populates the fields of the passed Geocerca object
        async def _fake_refresh(obj: Any, **_: Any) -> None:
            obj.id = new_geocerca.id
            obj.version = 1
            obj.vigente = True
            obj.created_at = new_geocerca.created_at
            obj.updated_at = new_geocerca.updated_at
            obj.hash_geometria = new_geocerca.hash_geometria
            obj.importado_en = new_geocerca.importado_en
            obj.importado_por = None

        svc.session.refresh = _fake_refresh

        with patch("aditsystem_backend.services.geocerca.from_shape", return_value=MagicMock()):
            with patch(
                "aditsystem_backend.services.geocerca.shape",
                return_value=MagicMock(is_valid=True, is_empty=False),
            ):
                payload = GeocercaCreate(
                    tipo=TipoGeocerca.ESTADO,
                    nombre="Guerrero",
                    codigo="12",
                    fuente="states.geojson",
                    geojson_geometry=_POLYGON_GEOJSON,
                )
                result = await svc.create(payload)

        assert result is not None
        svc.repo.create.assert_called_once()


# ---------------------------------------------------------------------------
# GeocercaService.get_or_404
# ---------------------------------------------------------------------------

class TestGeocercaServiceGetOr404:
    @pytest.mark.asyncio
    async def test_raises_404_when_not_found(self) -> None:
        svc = _service_with_mocked_repo(repo_get=None)
        with pytest.raises(DomainError) as exc_info:
            await svc.get_or_404("nonexistent-id")
        assert exc_info.value.status_code == 404

    @pytest.mark.asyncio
    async def test_returns_geocerca_when_found(self) -> None:
        g = _make_geocerca()
        svc = _service_with_mocked_repo(repo_get=g)
        result = await svc.get_or_404(g.id)
        assert result.id == g.id


# ---------------------------------------------------------------------------
# GeocercaService.deactivate
# ---------------------------------------------------------------------------

class TestGeocercaServiceDeactivate:
    @pytest.mark.asyncio
    async def test_deactivate_active_geocerca(self) -> None:
        g = _make_geocerca(vigente=True)
        svc = _service_with_mocked_repo(repo_get=g)

        with patch("aditsystem_backend.services.geocerca.GeocercaRead.model_validate", return_value=MagicMock()):
            await svc.deactivate(g.id)

        assert g.vigente is False

    @pytest.mark.asyncio
    async def test_raises_if_already_inactive(self) -> None:
        g = _make_geocerca(vigente=False)
        svc = _service_with_mocked_repo(repo_get=g)
        with pytest.raises(DomainError, match="ya está inactiva"):
            await svc.deactivate(g.id)


# ---------------------------------------------------------------------------
# GeocercaService.import_geojson
# ---------------------------------------------------------------------------

class TestGeocercaServiceImportGeoJSON:
    @pytest.mark.asyncio
    async def test_rejects_non_feature_collection(self) -> None:
        svc = _service_with_mocked_repo()
        with pytest.raises(DomainError, match="FeatureCollection"):
            await svc.import_geojson(
                {"type": "Feature"}, TipoGeocerca.ESTADO, "test.geojson"
            )

    @pytest.mark.asyncio
    async def test_rejects_unsupported_crs(self) -> None:
        svc = _service_with_mocked_repo()
        fc = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:3857"}},
            "features": [],
        }
        with pytest.raises(DomainError, match="CRS"):
            await svc.import_geojson(fc, TipoGeocerca.ESTADO, "test.geojson")

    @pytest.mark.asyncio
    async def test_skips_duplicate_geometry(self) -> None:
        existing = _make_geocerca()
        svc = _service_with_mocked_repo(repo_get_by_hash=existing)

        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"state_code": 9, "state_name": "DF"},
                    "geometry": _POLYGON_GEOJSON,
                }
            ],
        }
        result = await svc.import_geojson(fc, TipoGeocerca.ESTADO, "states.geojson")
        assert result["skipped"] == 1
        assert result["created"] == 0

    @pytest.mark.asyncio
    async def test_skips_non_polygon_geometry(self) -> None:
        svc = _service_with_mocked_repo(repo_get_by_hash=None)

        fc = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {"state_code": 9, "state_name": "DF"},
                    "geometry": {"type": "Point", "coordinates": [-99.0, 19.0]},
                }
            ],
        }
        result = await svc.import_geojson(fc, TipoGeocerca.ESTADO, "states.geojson")
        assert result["errors"] == 1
        assert result["created"] == 0


# ---------------------------------------------------------------------------
# GeocercaService.import_kml
# ---------------------------------------------------------------------------

class TestGeocercaServiceImportKML:
    _SIMPLE_KML = """\
<?xml version="1.0" encoding="utf-8" ?>
<kml xmlns="http://www.opengis.net/kml/2.2">
<Document id="root_doc">
<Folder><name>distrito_local</name>
  <Placemark>
    <ExtendedData>
      <SchemaData>
        <SimpleData name="id">1</SimpleData>
        <SimpleData name="entidad">21</SimpleData>
        <SimpleData name="distrito_l">1</SimpleData>
      </SchemaData>
    </ExtendedData>
    <Polygon>
      <outerBoundaryIs><LinearRing>
        <coordinates>
          -98.27,19.04 -98.28,19.05 -98.26,19.06 -98.27,19.04
        </coordinates>
      </LinearRing></outerBoundaryIs>
    </Polygon>
  </Placemark>
</Folder>
</Document>
</kml>"""

    @pytest.mark.asyncio
    async def test_parses_simple_kml(self) -> None:
        svc = _service_with_mocked_repo(repo_get_by_hash=None)
        with patch("aditsystem_backend.services.geocerca.from_shape", return_value=MagicMock()):
            with patch(
                "aditsystem_backend.services.geocerca.shape",
                return_value=MagicMock(is_valid=True, is_empty=False),
            ):
                result = await svc.import_kml(
                    self._SIMPLE_KML,
                    tipo=TipoGeocerca.DISTRITO,
                    fuente="distritos.kml",
                )
        assert result["created"] == 1
        assert result["errors"] == 0

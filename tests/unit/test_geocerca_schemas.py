"""Unit tests for Geocerca Pydantic schemas."""

import pytest

from aditsystem_backend.models.enums import TipoGeocerca
from aditsystem_backend.schemas.geocerca import (
    ContainsPointRequest,
    GeocercaCreate,
    GeocercaListParams,
)

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

_MULTIPOLYGON_GEOJSON = {
    "type": "MultiPolygon",
    "coordinates": [
        [
            [
                [-99.09, 19.50],
                [-99.06, 19.49],
                [-99.05, 19.42],
                [-99.12, 19.40],
                [-99.09, 19.50],
            ]
        ]
    ],
}


def _base_payload(geom: dict | None = None) -> dict:
    return {
        "tipo": TipoGeocerca.ESTADO,
        "nombre": "Distrito Federal",
        "codigo": "9",
        "codigo_padre": None,
        "fuente": "states.geojson",
        "geojson_geometry": geom or _POLYGON_GEOJSON,
    }


class TestGeocercaCreate:
    def test_accepts_polygon(self) -> None:
        g = GeocercaCreate(**_base_payload(_POLYGON_GEOJSON))
        assert g.nombre == "Distrito Federal"
        assert g.tipo == TipoGeocerca.ESTADO

    def test_accepts_multipolygon(self) -> None:
        g = GeocercaCreate(**_base_payload(_MULTIPOLYGON_GEOJSON))
        assert g.geojson_geometry["type"] == "MultiPolygon"

    def test_rejects_point_geometry(self) -> None:
        bad_geom = {"type": "Point", "coordinates": [-99.09, 19.50]}
        with pytest.raises(ValueError, match="geometry type"):
            GeocercaCreate(**_base_payload(bad_geom))

    def test_rejects_linestring_geometry(self) -> None:
        bad_geom = {
            "type": "LineString",
            "coordinates": [[-99.09, 19.50], [-99.06, 19.49]],
        }
        with pytest.raises(ValueError, match="geometry type"):
            GeocercaCreate(**_base_payload(bad_geom))

    def test_nombre_cannot_be_empty(self) -> None:
        payload = _base_payload()
        payload["nombre"] = ""
        with pytest.raises(ValueError):
            GeocercaCreate(**payload)

    def test_optional_importado_por(self) -> None:
        g = GeocercaCreate(**{**_base_payload(), "importado_por": "batch-001"})
        assert g.importado_por == "batch-001"


class TestContainsPointRequest:
    def test_valid_coordinates(self) -> None:
        req = ContainsPointRequest(latitud=19.43, longitud=-99.13)
        assert req.latitud == 19.43
        assert req.longitud == -99.13

    def test_rejects_invalid_lat(self) -> None:
        with pytest.raises(ValueError):
            ContainsPointRequest(latitud=91.0, longitud=-99.13)

    def test_rejects_invalid_lng(self) -> None:
        with pytest.raises(ValueError):
            ContainsPointRequest(latitud=19.43, longitud=181.0)

    def test_tipo_optional(self) -> None:
        req = ContainsPointRequest(latitud=19.43, longitud=-99.13, tipo=TipoGeocerca.ESTADO)
        assert req.tipo == TipoGeocerca.ESTADO


class TestGeocercaListParams:
    def test_defaults(self) -> None:
        p = GeocercaListParams()
        assert p.vigente is True
        assert p.page == 1
        assert p.page_size == 50

    def test_page_size_max(self) -> None:
        with pytest.raises(ValueError):
            GeocercaListParams(page_size=201)

    def test_page_must_be_positive(self) -> None:
        with pytest.raises(ValueError):
            GeocercaListParams(page=0)

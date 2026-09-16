from datetime import UTC, datetime
from decimal import Decimal

import pytest

from aditsystem_backend.schemas.politico import PoliticoCreate, PoliticoUpdate


def base_payload() -> dict:
    return {
        "nombre": "Juan",
        "apellido_paterno": "Perez",
        "apellido_materno": "Lopez",
        "telefono": "5500000001",
        "fecha_registro": datetime.now(UTC),
    }


def test_politico_create_accepts_valid_payload() -> None:
    p = PoliticoCreate(**base_payload())
    assert p.nombre == "Juan"


def test_politico_create_requires_nombre() -> None:
    payload = base_payload()
    del payload["nombre"]
    with pytest.raises(ValueError):
        PoliticoCreate(**payload)


def test_politico_create_requires_telefono() -> None:
    payload = base_payload()
    del payload["telefono"]
    with pytest.raises(ValueError):
        PoliticoCreate(**payload)


def test_politico_create_accepts_optional_geo_fields() -> None:
    payload = base_payload()
    payload["latitud"] = Decimal("19.43")
    payload["longitud"] = Decimal("-99.13")
    payload["municipio"] = "CDMX"
    p = PoliticoCreate(**payload)
    assert p.municipio == "CDMX"


def test_politico_create_rejects_out_of_range_latitud() -> None:
    payload = base_payload()
    payload["latitud"] = Decimal("91.0")
    with pytest.raises(ValueError):
        PoliticoCreate(**payload)


def test_politico_update_all_optional() -> None:
    update = PoliticoUpdate()
    assert update.nombre is None
    assert update.estatus is None


def test_politico_update_accepts_partial_fields() -> None:
    update = PoliticoUpdate(nombre="Maria", municipio="Guadalajara")
    assert update.nombre == "Maria"
    assert update.telefono is None

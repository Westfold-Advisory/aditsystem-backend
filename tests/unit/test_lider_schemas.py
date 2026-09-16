from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aditsystem_backend.schemas.lider import LiderCreate, LiderUpdate


def base_payload() -> dict:
    return {
        "nombre": "Ana",
        "apellido_paterno": "Garcia",
        "apellido_materno": "Ruiz",
        "telefono": "5500000002",
        "fecha_registro": datetime.now(UTC),
        "politico_id": uuid4(),
    }


def test_lider_create_accepts_valid_payload() -> None:
    lider = LiderCreate(**base_payload())
    assert lider.nombre == "Ana"


def test_lider_create_requires_politico_id() -> None:
    payload = base_payload()
    del payload["politico_id"]
    with pytest.raises(ValueError):
        LiderCreate(**payload)


def test_lider_create_requires_nombre() -> None:
    payload = base_payload()
    del payload["nombre"]
    with pytest.raises(ValueError):
        LiderCreate(**payload)


def test_lider_update_all_optional() -> None:
    update = LiderUpdate()
    assert update.nombre is None
    assert update.estatus is None
    assert update.url_mapa is None


def test_lider_update_accepts_estatus() -> None:
    from aditsystem_backend.models.enums import EstatusPersona

    update = LiderUpdate(estatus=EstatusPersona.INACTIVO)
    assert update.estatus == EstatusPersona.INACTIVO

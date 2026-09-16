from datetime import UTC, datetime
from uuid import uuid4

import pytest

from aditsystem_backend.schemas.invitado import InvitadoCreate, InvitadoUpdate


def base_payload() -> dict:
    return {
        "nombre": "Carlos",
        "apellido_paterno": "Mendez",
        "apellido_materno": "Torres",
        "telefono": "5500000003",
        "fecha_registro": datetime.now(UTC),
        "lider_id": uuid4(),
    }


def test_invitado_create_accepts_valid_payload() -> None:
    inv = InvitadoCreate(**base_payload())
    assert inv.nombre == "Carlos"


def test_invitado_create_requires_lider_id() -> None:
    payload = base_payload()
    del payload["lider_id"]
    with pytest.raises(ValueError):
        InvitadoCreate(**payload)


def test_invitado_create_requires_telefono() -> None:
    payload = base_payload()
    del payload["telefono"]
    with pytest.raises(ValueError):
        InvitadoCreate(**payload)


def test_invitado_create_accepts_optional_fuente() -> None:
    payload = base_payload()
    payload["fuente_registro"] = "EVENTO"
    inv = InvitadoCreate(**payload)
    assert inv.fuente_registro == "EVENTO"


def test_invitado_update_all_optional() -> None:
    update = InvitadoUpdate()
    assert update.nombre is None
    assert update.estatus is None

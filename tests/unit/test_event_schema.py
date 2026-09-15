from datetime import UTC, datetime, timedelta
from decimal import Decimal

import pytest

from aditsystem_backend.schemas.event import EventCreate


def build_payload() -> dict:
    start = datetime.now(UTC)
    return {
        "tipo": "REUNION",
        "nombre": "Evento prueba",
        "descripcion": "Descripcion",
        "latitud": Decimal("19.432608"),
        "longitud": Decimal("-99.133209"),
        "ubicacion_texto": "Centro Historico",
        "fecha_inicio": start,
        "fecha_fin": start + timedelta(hours=2),
        "checkin_abierto_desde": start - timedelta(minutes=30),
        "checkin_abierto_hasta": start + timedelta(hours=1),
        "capacidad_maxima": 50,
        "checkin_radio_metros": 100,
    }


def test_event_schema_accepts_valid_payload() -> None:
    event = EventCreate(**build_payload())
    assert event.nombre == "Evento prueba"


def test_event_schema_rejects_invalid_dates() -> None:
    payload = build_payload()
    payload["fecha_fin"] = payload["fecha_inicio"] - timedelta(minutes=1)

    with pytest.raises(ValueError):
        EventCreate(**payload)

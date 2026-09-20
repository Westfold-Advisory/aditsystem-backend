from decimal import Decimal

import pytest
from pydantic import ValidationError

from aditsystem_backend.models.enums import NecesidadComunidad
from aditsystem_backend.schemas.persona import PersonaCreate, PersonaUpdate


def test_persona_create_accepts_direccion_and_necesidades() -> None:
    payload = PersonaCreate(
        rol="AMIGO",
        parent_persona_id=None,
        nombre="Ana",
        apellido_paterno="López",
        apellido_materno="Ruiz",
        telefono="2221234567",
        calle="Av. Juárez",
        numero_exterior="100",
        colonia="Centro",
        codigo_postal="72000",
        latitud=Decimal("19.043300"),
        longitud=Decimal("-98.201900"),
        necesidades_comunidad=[
            NecesidadComunidad.INSEGURIDAD,
            NecesidadComunidad.FALTA_AGUA_POTABLE,
        ],
    )
    assert payload.necesidades_comunidad is not None
    assert len(payload.necesidades_comunidad) == 2


def test_persona_create_rejects_partial_coordinates() -> None:
    with pytest.raises(ValidationError, match="latitud y longitud"):
        PersonaCreate(
            rol="AMIGO",
            nombre="Ana",
            apellido_paterno="López",
            apellido_materno="Ruiz",
            telefono="2221234567",
            latitud=Decimal("19.0"),
        )


def test_persona_create_rejects_more_than_three_necesidades() -> None:
    with pytest.raises(ValidationError, match="máximo 3"):
        PersonaCreate(
            rol="AMIGO",
            nombre="Ana",
            apellido_paterno="López",
            apellido_materno="Ruiz",
            telefono="2221234567",
            necesidades_comunidad=[
                NecesidadComunidad.INSEGURIDAD,
                NecesidadComunidad.FALTA_AGUA_POTABLE,
                NecesidadComunidad.FALTA_EMPLEO,
                NecesidadComunidad.FALTA_LIMPIEZA,
            ],
        )


def test_persona_update_deduplicates_necesidades() -> None:
    payload = PersonaUpdate(
        necesidades_comunidad=[
            NecesidadComunidad.INSEGURIDAD,
            NecesidadComunidad.INSEGURIDAD,
        ]
    )
    assert payload.necesidades_comunidad == [NecesidadComunidad.INSEGURIDAD]

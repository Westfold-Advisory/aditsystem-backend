from types import SimpleNamespace
from unittest.mock import patch

import pytest

from aditsystem_backend.cli.bootstrap_admin import BootstrapError
from aditsystem_backend.cli.seed_faker import (
    DEFAULT_DOMAIN,
    SeedFakerConfig,
    _example_cv_pdf,
    _role_email,
    _validate_runtime,
    _write_asset,
    count_planned_people,
    iter_planned_people,
)
from aditsystem_backend.models.enums import PersonRole


def test_default_config_person_count() -> None:
    config = SeedFakerConfig()
    assert count_planned_people(config) == 338


def test_planned_hierarchy_respects_tree_and_amigo_has_no_email() -> None:
    config = SeedFakerConfig(
        coordinadores_generales=1,
        coordinadores_por_cg=1,
        enlaces_por_coordinador=1,
        amigos_por_enlace=2,
        faker_seed=7,
    )
    people = list(iter_planned_people(config))
    assert len(people) == 5
    roles = [person.role for person in people]
    assert roles == [
        PersonRole.COORDINADOR_GENERAL,
        PersonRole.COORDINADOR,
        PersonRole.ENLACE,
        PersonRole.AMIGO,
        PersonRole.AMIGO,
    ]
    amigos = [person for person in people if person.role is PersonRole.AMIGO]
    assert all(person.email is None for person in amigos)
    assert all(person.telefono.startswith("55599") for person in amigos)


def test_authenticable_emails_use_fictitious_domain() -> None:
    config = SeedFakerConfig(faker_seed=1)
    auth_people = [
        person
        for person in iter_planned_people(config)
        if person.role is not PersonRole.AMIGO
    ]
    assert auth_people
    assert all(
        person.email and person.email.endswith(f"@{DEFAULT_DOMAIN}")
        for person in auth_people
    )
    assert all(
        person.email and person.email.startswith("faker.") for person in auth_people
    )


def test_role_email_is_stable() -> None:
    assert (
        _role_email(
            PersonRole.ENLACE,
            domain="aditsystem.test",
            cg_index=0,
            co_index=2,
            en_index=4,
        )
        == "faker.en.0.2.4@aditsystem.test"
    )


def test_faker_seed_makes_names_deterministic() -> None:
    config = SeedFakerConfig(
        coordinadores_generales=1,
        coordinadores_por_cg=1,
        enlaces_por_coordinador=1,
        amigos_por_enlace=1,
        faker_seed=99,
    )
    first = list(iter_planned_people(config))
    second = list(iter_planned_people(config))
    assert [(p.nombre, p.apellido_paterno) for p in first] == [
        (p.nombre, p.apellido_paterno) for p in second
    ]


def test_planned_people_have_deterministic_mappable_coordinates() -> None:
    config = SeedFakerConfig(
        coordinadores_generales=2,
        coordinadores_por_cg=1,
        enlaces_por_coordinador=1,
        amigos_por_enlace=2,
    )
    people = list(iter_planned_people(config))
    assert all(-90 <= person.latitud <= 90 for person in people)
    assert all(-180 <= person.longitud <= 180 for person in people)
    assert len({(person.latitud, person.longitud) for person in people}) > 2


def test_demo_assets_are_valid_pdf_and_idempotently_written(tmp_path) -> None:
    persona = SimpleNamespace(nombre="Ana", apellido_paterno="Prueba")
    pdf = _example_cv_pdf(persona)
    assert pdf.startswith(b"%PDF-1.4")
    assert pdf.endswith(b"%%EOF\n")
    assert _write_asset(tmp_path, "demo/faker/cv.pdf", pdf) == len(pdf)
    assert (tmp_path / "demo/faker/cv.pdf").read_bytes() == pdf


@pytest.mark.parametrize("environment", ["production", "qa", "test"])
def test_seed_faker_rejects_non_development_environments(environment: str) -> None:
    with patch(
        "aditsystem_backend.cli.seed_faker.get_settings",
        return_value=SimpleNamespace(app_env=environment),
    ):
        with pytest.raises(BootstrapError, match="local o development"):
            _validate_runtime()

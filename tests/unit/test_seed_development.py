from types import SimpleNamespace
from unittest.mock import patch

import pytest

from aditsystem_backend.cli.bootstrap_admin import BootstrapError
from aditsystem_backend.cli.seed_development import (
    SEED_PEOPLE,
    _validate_runtime,
)
from aditsystem_backend.models.enums import PersonRole


def test_seed_is_fictitious_and_leaves_amigo_without_an_account() -> None:
    assert all(
        person.email is None or person.email.endswith("@aditsystem.test")
        for person in SEED_PEOPLE
    )
    amigo = next(person for person in SEED_PEOPLE if person.role is PersonRole.AMIGO)
    assert amigo.email is None
    assert {person.role for person in SEED_PEOPLE} == {
        PersonRole.ADMIN,
        PersonRole.COORDINADOR_GENERAL,
        PersonRole.COORDINADOR,
        PersonRole.ENLACE,
        PersonRole.AMIGO,
    }


@pytest.mark.parametrize("environment", ["production", "qa", "test"])
def test_seed_rejects_non_development_environments(environment: str) -> None:
    with patch(
        "aditsystem_backend.cli.seed_development.get_settings",
        return_value=SimpleNamespace(app_env=environment),
    ):
        with pytest.raises(BootstrapError, match="local o development"):
            _validate_runtime()

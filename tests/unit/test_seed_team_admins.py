from types import SimpleNamespace
from unittest.mock import patch

import pytest

from aditsystem_backend.cli.bootstrap_admin import BootstrapError
from aditsystem_backend.cli.seed_team_admins import (
    _persona_fields_for_email,
    _validate_runtime,
    parse_team_admin_emails,
)


def test_parse_team_admin_emails_deduplicates_and_normalizes() -> None:
    emails = parse_team_admin_emails(
        "Brandon.Roldan@Example.com, brandon.roldan@example.com, "
        "ramirezmarco935@gmail.com"
    )
    assert emails == ("brandon.roldan@example.com", "ramirezmarco935@gmail.com")


def test_parse_team_admin_emails_rejects_empty() -> None:
    with pytest.raises(BootstrapError, match="TEAM_ADMIN_EMAILS"):
        parse_team_admin_emails("  ,  ")


def test_persona_fields_derive_from_local_part() -> None:
    fields = _persona_fields_for_email("brandon.roldan.br2@gmail.com", 1)
    assert fields["nombre"] == "Brandon"
    assert fields["apellido_paterno"] == "Roldan"
    assert fields["telefono"].startswith("555")


@pytest.mark.parametrize("environment", ["production", "staging"])
def test_team_admin_seed_rejects_non_development_environments(
    environment: str,
) -> None:
    with patch(
        "aditsystem_backend.cli.seed_team_admins.get_settings",
        return_value=SimpleNamespace(app_env=environment),
    ):
        with pytest.raises(BootstrapError, match="local o development"):
            _validate_runtime()

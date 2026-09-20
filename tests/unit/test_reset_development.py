from types import SimpleNamespace

import pytest

from aditsystem_backend.cli.reset_development import ResetError, validate_reset_request


def _settings(*, app_env: str = "development", host: str = "aditsystem-dev.abc.us-east-1.rds.amazonaws.com"):
    return SimpleNamespace(
        app_env=app_env,
        database_url=f"postgresql+asyncpg://user:password@{host}:5432/aditsystem",
    )


def test_reset_accepts_only_exact_development_rds_host() -> None:
    host = "aditsystem-dev.abc.us-east-1.rds.amazonaws.com"

    assert (
        validate_reset_request(
            settings=_settings(host=host),
            confirmation="RESET_DEVELOPMENT_DATA",
            expected_host=host,
            change_id="CHG-123",
        )
        == host
    )


@pytest.mark.parametrize(
    ("app_env", "confirmation", "expected_host"),
    [
        ("production", "RESET_DEVELOPMENT_DATA", "aditsystem-dev.abc.us-east-1.rds.amazonaws.com"),
        ("development", "wrong", "aditsystem-dev.abc.us-east-1.rds.amazonaws.com"),
        ("development", "RESET_DEVELOPMENT_DATA", "other.abc.us-east-1.rds.amazonaws.com"),
    ],
)
def test_reset_rejects_missing_or_mismatched_guards(
    app_env: str, confirmation: str, expected_host: str
) -> None:
    with pytest.raises(ResetError):
        validate_reset_request(
            settings=_settings(app_env=app_env),
            confirmation=confirmation,
            expected_host=expected_host,
            change_id="CHG-123",
        )


def test_reset_rejects_production_named_rds_endpoint() -> None:
    host = "aditsystem-prod.abc.us-east-1.rds.amazonaws.com"

    with pytest.raises(ResetError, match="allowed development"):
        validate_reset_request(
            settings=_settings(host=host),
            confirmation="RESET_DEVELOPMENT_DATA",
            expected_host=host,
            change_id="CHG-123",
        )

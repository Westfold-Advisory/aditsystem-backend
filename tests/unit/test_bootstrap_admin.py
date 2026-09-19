"""Unit tests for aditsystem_backend.cli.bootstrap_admin."""
import sys
from types import ModuleType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aditsystem_backend.cli.bootstrap_admin import (
    BootstrapError,
    _fetch_secret,
    _validate_email,
    _validate_password,
    bootstrap_admin,
    resolve_password,
)
from aditsystem_backend.models.enums import UserRole
from aditsystem_backend.models.user import User


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_session(existing_user: User | None = None) -> AsyncMock:
    session = AsyncMock()
    result_mock = MagicMock()
    result_mock.scalar_one_or_none.return_value = existing_user
    session.execute = AsyncMock(return_value=result_mock)
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


def _make_user(role: UserRole) -> MagicMock:
    user = MagicMock(spec=User)
    user.role = role
    return user


# ---------------------------------------------------------------------------
# resolve_password
# ---------------------------------------------------------------------------


def test_resolve_password_prefers_secrets_manager(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("BOOTSTRAP_PASSWORD_SECRET_ID", "prod/admin-password")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "should-not-be-used")

    with patch(
        "aditsystem_backend.cli.bootstrap_admin._fetch_secret", return_value="sm_value"
    ) as mock_fetch:
        result = resolve_password()

    mock_fetch.assert_called_once_with("prod/admin-password")
    assert result == "sm_value"


def test_resolve_password_falls_back_to_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOOTSTRAP_PASSWORD_SECRET_ID", raising=False)
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "env_secret_pass")

    assert resolve_password() == "env_secret_pass"


def test_resolve_password_raises_when_nothing_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("BOOTSTRAP_PASSWORD_SECRET_ID", raising=False)
    monkeypatch.delenv("BOOTSTRAP_PASSWORD", raising=False)

    with pytest.raises(BootstrapError) as exc_info:
        resolve_password()

    assert exc_info.value.exit_code == 1
    assert "BOOTSTRAP_PASSWORD" in str(exc_info.value)


def test_fetch_secret_raises_when_boto3_missing() -> None:
    fake_modules: dict[str, ModuleType | None] = {"boto3": None}
    with patch.dict(sys.modules, fake_modules):
        with pytest.raises(BootstrapError, match="boto3"):
            _fetch_secret("some/secret")


def test_fetch_secret_raises_on_client_error() -> None:
    boto3_mock = MagicMock()
    botocore_mock = MagicMock()
    client_mock = MagicMock()
    boto3_mock.client.return_value = client_mock

    error_response = {"Error": {"Code": "ResourceNotFoundException", "Message": "not found"}}
    client_error_class = type("ClientError", (Exception,), {"response": error_response})
    botocore_mock.exceptions.ClientError = client_error_class
    client_mock.get_secret_value.side_effect = client_error_class(
        error_response, "GetSecretValue"
    )
    client_error_class.response = error_response

    with (
        patch.dict(sys.modules, {"boto3": boto3_mock, "botocore": botocore_mock, "botocore.exceptions": botocore_mock.exceptions}),
        pytest.raises(BootstrapError, match="ResourceNotFoundException"),
    ):
        _fetch_secret("missing/secret")


# ---------------------------------------------------------------------------
# _validate_email
# ---------------------------------------------------------------------------


def test_validate_email_normalizes_to_lowercase() -> None:
    assert _validate_email("Admin@Example.COM") == "admin@example.com"


def test_validate_email_raises_on_missing_at() -> None:
    with pytest.raises(BootstrapError):
        _validate_email("not-an-email")


def test_validate_email_raises_on_empty() -> None:
    with pytest.raises(BootstrapError):
        _validate_email("")


# ---------------------------------------------------------------------------
# _validate_password
# ---------------------------------------------------------------------------


def test_validate_password_accepts_8_chars() -> None:
    _validate_password("12345678")  # must not raise


def test_validate_password_rejects_short() -> None:
    with pytest.raises(BootstrapError):
        _validate_password("short")


# ---------------------------------------------------------------------------
# bootstrap_admin — success: new user created
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_creates_admin_user() -> None:
    session = _make_session(existing_user=None)

    with patch(
        "aditsystem_backend.cli.bootstrap_admin.hash_password",
        return_value="$2b$12$fakehash",
    ):
        await bootstrap_admin(
            email="admin@example.com",
            full_name="Admin User",
            password="SecurePass1",
            session=session,
        )

    session.add.assert_called_once()
    user_arg: User = session.add.call_args[0][0]
    assert isinstance(user_arg, User)
    assert user_arg.email == "admin@example.com"
    assert user_arg.full_name == "Admin User"
    assert user_arg.role == UserRole.ADMIN
    assert user_arg.password_hash == "$2b$12$fakehash"
    session.commit.assert_called_once()


# ---------------------------------------------------------------------------
# bootstrap_admin — idempotency: already ADMIN
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent_when_admin_exists() -> None:
    session = _make_session(existing_user=_make_user(UserRole.ADMIN))

    await bootstrap_admin(
        email="admin@example.com",
        full_name="Admin User",
        password="SecurePass1",
        session=session,
    )

    session.add.assert_not_called()
    session.commit.assert_not_called()


# ---------------------------------------------------------------------------
# bootstrap_admin — conflict: exists with different role
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "conflicting_role",
    [UserRole.POLITICO, UserRole.LIDER, UserRole.INVITADO],
)
async def test_bootstrap_raises_on_role_conflict(conflicting_role: UserRole) -> None:
    session = _make_session(existing_user=_make_user(conflicting_role))

    with pytest.raises(BootstrapError) as exc_info:
        await bootstrap_admin(
            email="admin@example.com",
            full_name="Admin User",
            password="SecurePass1",
            session=session,
        )

    assert exc_info.value.exit_code == 1
    assert conflicting_role.value in str(exc_info.value)
    session.add.assert_not_called()
    session.commit.assert_not_called()

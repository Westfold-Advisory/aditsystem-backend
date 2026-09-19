"""Tests for the controlled final-model ADMIN bootstrap CLI."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aditsystem_backend.cli.bootstrap_admin import (
    AUTHORIZED_BOOTSTRAP_EMAIL,
    BootstrapError,
    _validate_runtime,
    bootstrap_admin,
    resolve_password,
)
from aditsystem_backend.models.enums import PersonRole


def _make_session(existing_user: object | None = None) -> AsyncMock:
    session = AsyncMock()
    result = MagicMock()
    result.scalar_one_or_none.return_value = existing_user
    session.execute.return_value = result
    session.add = MagicMock()
    session.commit = AsyncMock()
    return session


def test_resolve_password_requires_a_secret_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("BOOTSTRAP_PASSWORD_SECRET_ID", raising=False)
    monkeypatch.delenv("BOOTSTRAP_PASSWORD", raising=False)
    with pytest.raises(BootstrapError, match="No password source"):
        resolve_password()


def test_resolve_password_prefers_secret_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOOTSTRAP_PASSWORD_SECRET_ID", "aditsystem/dev/bootstrap-admin")
    monkeypatch.setenv("BOOTSTRAP_PASSWORD", "not-used")
    with patch(
        "aditsystem_backend.cli.bootstrap_admin._fetch_secret",
        return_value="secret-value",
    ):
        assert resolve_password() == "secret-value"


@pytest.mark.parametrize("environment", ["production", "staging", "test"])
def test_runtime_rejects_non_local_development_environments(environment: str) -> None:
    settings = SimpleNamespace(app_env=environment)
    with pytest.raises(BootstrapError, match="local or development"):
        _validate_runtime(settings=settings, email=AUTHORIZED_BOOTSTRAP_EMAIL)


def test_runtime_rejects_an_unauthorised_email() -> None:
    settings = SimpleNamespace(app_env="development")
    with pytest.raises(BootstrapError, match="not authorised"):
        _validate_runtime(settings=settings, email="other@example.com")


@pytest.mark.asyncio
async def test_bootstrap_creates_only_active_admin_pair(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOOTSTRAP_NOMBRE", "Ervic")
    session = _make_session()
    with patch(
        "aditsystem_backend.cli.bootstrap_admin.hash_password", return_value="hash"
    ):
        await bootstrap_admin(
            email=AUTHORIZED_BOOTSTRAP_EMAIL, password="SecurePass1", session=session
        )

    auth_user = session.add.call_args.args[0]
    assert auth_user.email == AUTHORIZED_BOOTSTRAP_EMAIL
    assert auth_user.is_active is True
    assert auth_user.password_hash == "hash"
    assert auth_user.persona.rol is PersonRole.ADMIN
    assert auth_user.persona.parent_persona_id is None
    assert auth_user.persona.nombre == "Ervic"
    session.commit.assert_awaited_once()


@pytest.mark.asyncio
async def test_bootstrap_is_idempotent_for_existing_active_admin() -> None:
    existing = SimpleNamespace(
        is_active=True,
        persona=SimpleNamespace(rol=PersonRole.ADMIN, deleted_at=None),
    )
    session = _make_session(existing)
    await bootstrap_admin(
        email=AUTHORIZED_BOOTSTRAP_EMAIL, password="SecurePass1", session=session
    )
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
async def test_bootstrap_rejects_inactive_existing_admin() -> None:
    existing = SimpleNamespace(
        is_active=False,
        persona=SimpleNamespace(rol=PersonRole.ADMIN, deleted_at=None),
    )
    session = _make_session(existing)
    with pytest.raises(BootstrapError, match="incompatible"):
        await bootstrap_admin(
            email=AUTHORIZED_BOOTSTRAP_EMAIL,
            password="SecurePass1",
            session=session,
        )
    session.add.assert_not_called()
    session.commit.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "role", [PersonRole.COORDINADOR, PersonRole.ENLACE, PersonRole.AMIGO]
)
async def test_bootstrap_rejects_incompatible_existing_account(
    role: PersonRole,
) -> None:
    existing = SimpleNamespace(
        is_active=True,
        persona=SimpleNamespace(rol=role, deleted_at=None),
    )
    session = _make_session(existing)
    with pytest.raises(BootstrapError, match="incompatible"):
        await bootstrap_admin(
            email=AUTHORIZED_BOOTSTRAP_EMAIL, password="SecurePass1", session=session
        )
    session.add.assert_not_called()
    session.commit.assert_not_awaited()

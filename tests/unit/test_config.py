from pathlib import Path

import pytest

from aditsystem_backend.core.config import Settings
from aditsystem_backend.core.exceptions import DomainError


def test_jwt_private_key_missing_raises_domain_error(tmp_path: Path) -> None:
    settings = Settings(jwt_private_key_path=tmp_path / "missing-private.pem")

    with pytest.raises(DomainError) as error:
        _ = settings.jwt_private_key

    assert error.value.status_code == 500


def test_jwt_public_key_missing_raises_domain_error(tmp_path: Path) -> None:
    settings = Settings(jwt_public_key_path=tmp_path / "missing-public.pem")

    with pytest.raises(DomainError) as error:
        _ = settings.jwt_public_key

    assert error.value.status_code == 500

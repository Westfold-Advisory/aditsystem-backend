from unittest.mock import MagicMock

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.services.persona_hierarchy import validate_parent


def person(role: PersonRole):
    value = MagicMock()
    value.rol = role
    value.deleted_at = None
    return value


def test_final_hierarchy_accepts_each_valid_edge() -> None:
    validate_parent(PersonRole.COORDINADOR_GENERAL, None)
    validate_parent(PersonRole.COORDINADOR, person(PersonRole.COORDINADOR_GENERAL))
    validate_parent(PersonRole.ENLACE, person(PersonRole.COORDINADOR))
    validate_parent(PersonRole.AMIGO, person(PersonRole.ENLACE))


def test_amigo_requires_enlace_parent() -> None:
    with pytest.raises(DomainError, match="ENLACE"):
        validate_parent(PersonRole.AMIGO, person(PersonRole.COORDINADOR))

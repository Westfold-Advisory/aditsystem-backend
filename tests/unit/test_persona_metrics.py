from unittest.mock import MagicMock

from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.models.persona import Persona
from aditsystem_backend.services.persona import PersonaService


def test_role_counts_only_include_hierarchy_levels() -> None:
    descendants = [
        MagicMock(spec=Persona, rol=PersonRole.COORDINADOR),
        MagicMock(spec=Persona, rol=PersonRole.COORDINADOR),
        MagicMock(spec=Persona, rol=PersonRole.ENLACE),
        MagicMock(spec=Persona, rol=PersonRole.AMIGO),
        MagicMock(spec=Persona, rol=PersonRole.AMIGO),
        MagicMock(spec=Persona, rol=PersonRole.ADMIN),
    ]
    assert PersonaService._role_counts(descendants) == {
        "coordinadores": 2,
        "enlaces": 1,
        "amigos": 2,
    }

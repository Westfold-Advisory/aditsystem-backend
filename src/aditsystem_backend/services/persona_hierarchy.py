from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import PersonRole
from aditsystem_backend.models.persona import Persona


REQUIRED_PARENT_ROLE = {
    PersonRole.ADMIN: None,
    PersonRole.COORDINADOR_GENERAL: None,
    PersonRole.COORDINADOR: PersonRole.COORDINADOR_GENERAL,
    PersonRole.ENLACE: PersonRole.COORDINADOR,
    PersonRole.AMIGO: PersonRole.ENLACE,
}


def validate_parent(role: PersonRole, parent: Persona | None) -> None:
    required = REQUIRED_PARENT_ROLE[role]
    if required is None and parent is not None:
        raise DomainError(f"{role} debe ser raíz", status_code=422)
    if required is not None and (parent is None or parent.rol != required):
        raise DomainError(f"{role} requiere padre {required}", status_code=422)
    if parent and parent.deleted_at is not None:
        raise DomainError("la persona padre está dada de baja", status_code=422)

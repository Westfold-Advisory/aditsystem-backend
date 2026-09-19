"""Hierarchy validation for the Coordinador General → Coordinador chain (TRA-87).

Rules:
  GENERAL_COORDINATOR  — root only; parent_politico_id MUST be NULL
  COORDINATOR          — must have a GENERAL_COORDINATOR as direct parent

Cycle detection walks the parent chain upward; it is O(depth) and safe for
the shallow two-level hierarchy required by the current model.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import TipoPolitico
from aditsystem_backend.models.politico import Politico


# Required parent tipo for each politico tipo. None means "must be a root".
REQUIRED_PARENT_TIPO: dict[str, str | None] = {
    TipoPolitico.GENERAL_COORDINATOR: None,
    TipoPolitico.COORDINATOR: TipoPolitico.GENERAL_COORDINATOR,
}


def validate_tipo_and_parent(tipo: str, parent: Politico | None) -> None:
    """Validate that the (tipo, parent) combination is allowed by hierarchy rules."""
    if tipo not in REQUIRED_PARENT_TIPO:
        raise DomainError(
            f"tipo_politico inválido: '{tipo}'. "
            f"Valores permitidos: {', '.join(REQUIRED_PARENT_TIPO)}",
            status_code=422,
        )

    required = REQUIRED_PARENT_TIPO[tipo]

    if required is None:
        if parent is not None:
            raise DomainError(
                "GENERAL_COORDINATOR no puede tener padre; debe ser raíz de la jerarquía",
                status_code=422,
            )
    else:
        if parent is None:
            raise DomainError(
                f"{tipo} requiere un padre de tipo {required}",
                status_code=422,
            )
        if parent.deleted_at is not None:
            raise DomainError("el político padre ha sido dado de baja", status_code=422)
        if parent.tipo != required:
            raise DomainError(
                f"{tipo} solo puede depender de {required}; "
                f"el padre proporcionado es de tipo '{parent.tipo}'",
                status_code=422,
            )


async def detect_cycle(
    session: AsyncSession, politico_id: str, new_parent_id: str
) -> None:
    """Raise DomainError if setting new_parent_id as parent of politico_id creates a cycle.

    Walks the chain from new_parent_id upward; if it reaches politico_id, a cycle exists.
    """
    visited: set[str] = {politico_id}
    current: str | None = new_parent_id

    while current is not None:
        if current in visited:
            raise DomainError(
                "La asignación de padre crearía un ciclo en la jerarquía",
                status_code=422,
            )
        visited.add(current)
        result = await session.execute(
            select(Politico.parent_politico_id).where(Politico.id == current)
        )
        current = result.scalar_one_or_none()

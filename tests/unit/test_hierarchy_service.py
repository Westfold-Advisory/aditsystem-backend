"""Unit tests for hierarchy validation and cycle detection (TRA-87).

All tests are pure-Python; no database connection is required.
Async cycle-detection tests mock the SQLAlchemy session.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import TipoPolitico
from aditsystem_backend.models.politico import Politico
from aditsystem_backend.services.hierarchy import (
    detect_cycle,
    validate_tipo_and_parent,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_politico(tipo: str | None, parent_id: str | None = None, deleted: bool = False) -> Politico:
    p = MagicMock(spec=Politico)
    p.id = "aaaa"
    p.tipo = tipo
    p.parent_politico_id = parent_id
    p.deleted_at = object() if deleted else None
    return p


def make_general() -> Politico:
    return make_politico(TipoPolitico.GENERAL_COORDINATOR, parent_id=None)


def make_coordinator(parent_id: str = "gen-id") -> Politico:
    return make_politico(TipoPolitico.COORDINATOR, parent_id=parent_id)


# ---------------------------------------------------------------------------
# validate_tipo_and_parent — valid combinations
# ---------------------------------------------------------------------------


def test_general_with_no_parent_is_valid() -> None:
    validate_tipo_and_parent(TipoPolitico.GENERAL_COORDINATOR, parent=None)


def test_coordinator_with_general_parent_is_valid() -> None:
    parent = make_general()
    validate_tipo_and_parent(TipoPolitico.COORDINATOR, parent=parent)


# ---------------------------------------------------------------------------
# validate_tipo_and_parent — invalid combinations
# ---------------------------------------------------------------------------


def test_general_with_parent_raises() -> None:
    parent = make_general()
    with pytest.raises(DomainError) as exc_info:
        validate_tipo_and_parent(TipoPolitico.GENERAL_COORDINATOR, parent=parent)
    assert exc_info.value.status_code == 422
    assert "raíz" in str(exc_info.value)


def test_coordinator_without_parent_raises() -> None:
    with pytest.raises(DomainError) as exc_info:
        validate_tipo_and_parent(TipoPolitico.COORDINATOR, parent=None)
    assert exc_info.value.status_code == 422
    assert "requiere un padre" in str(exc_info.value)


def test_coordinator_with_coordinator_parent_raises() -> None:
    parent = make_coordinator()
    with pytest.raises(DomainError) as exc_info:
        validate_tipo_and_parent(TipoPolitico.COORDINATOR, parent=parent)
    assert exc_info.value.status_code == 422
    assert "GENERAL_COORDINATOR" in str(exc_info.value)


def test_coordinator_with_deleted_parent_raises() -> None:
    parent = make_general()
    parent.deleted_at = object()  # mark as soft-deleted
    with pytest.raises(DomainError) as exc_info:
        validate_tipo_and_parent(TipoPolitico.COORDINATOR, parent=parent)
    assert exc_info.value.status_code == 422
    assert "baja" in str(exc_info.value)


def test_invalid_tipo_raises() -> None:
    with pytest.raises(DomainError) as exc_info:
        validate_tipo_and_parent("UNKNOWN_TIPO", parent=None)
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# detect_cycle — async tests
# ---------------------------------------------------------------------------


def make_session_returning(*parent_ids: str | None) -> AsyncMock:
    """Build a mock session whose scalar results walk up the parent chain."""
    session = AsyncMock()
    results = [AsyncMock(scalar_one_or_none=MagicMock(return_value=pid)) for pid in parent_ids]
    session.execute = AsyncMock(side_effect=results)
    return session


@pytest.mark.asyncio
async def test_no_cycle_when_chain_is_clean() -> None:
    # politico_id="A", new_parent_id="B", B has no parent
    session = make_session_returning(None)
    await detect_cycle(session, politico_id="A", new_parent_id="B")  # must not raise


@pytest.mark.asyncio
async def test_no_cycle_for_linear_chain() -> None:
    # A wants to become child of B; B's parent is C; C has no parent
    session = make_session_returning("C", None)
    await detect_cycle(session, politico_id="A", new_parent_id="B")


@pytest.mark.asyncio
async def test_direct_self_parent_raises() -> None:
    # A trying to set its own parent to A
    session = make_session_returning(None)
    with pytest.raises(DomainError) as exc_info:
        await detect_cycle(session, politico_id="A", new_parent_id="A")
    assert exc_info.value.status_code == 422
    assert "ciclo" in str(exc_info.value)


@pytest.mark.asyncio
async def test_indirect_cycle_raises() -> None:
    # Current chain: B → C → A (A is ancestor of B); now A wants parent = B → cycle
    # detect_cycle walks from B upward: B's parent = C, C's parent = A → "A" in visited
    session = make_session_returning("C", "A", None)
    with pytest.raises(DomainError) as exc_info:
        await detect_cycle(session, politico_id="A", new_parent_id="B")
    assert exc_info.value.status_code == 422


# ---------------------------------------------------------------------------
# PoliticoCreate schema — hierarchy fields are optional
# ---------------------------------------------------------------------------


def test_politico_create_accepts_no_hierarchy_fields() -> None:
    from datetime import UTC, datetime

    from aditsystem_backend.schemas.politico import PoliticoCreate

    p = PoliticoCreate(
        nombre="Ana",
        apellido_paterno="Ruiz",
        apellido_materno="Lopez",
        telefono="5500000002",
        fecha_registro=datetime.now(UTC),
    )
    assert p.tipo is None
    assert p.parent_politico_id is None


def test_politico_create_accepts_general_coordinator_type() -> None:
    from datetime import UTC, datetime

    from aditsystem_backend.schemas.politico import PoliticoCreate

    p = PoliticoCreate(
        nombre="Juan",
        apellido_paterno="Perez",
        apellido_materno="Garcia",
        telefono="5500000003",
        fecha_registro=datetime.now(UTC),
        tipo=TipoPolitico.GENERAL_COORDINATOR,
    )
    assert p.tipo == TipoPolitico.GENERAL_COORDINATOR


def test_politico_create_accepts_coordinator_with_parent() -> None:
    import uuid
    from datetime import UTC, datetime

    from aditsystem_backend.schemas.politico import PoliticoCreate

    parent_id = uuid.uuid4()
    p = PoliticoCreate(
        nombre="Maria",
        apellido_paterno="Torres",
        apellido_materno="Vega",
        telefono="5500000004",
        fecha_registro=datetime.now(UTC),
        tipo=TipoPolitico.COORDINATOR,
        parent_politico_id=parent_id,
    )
    assert p.tipo == TipoPolitico.COORDINATOR
    assert p.parent_politico_id == parent_id

from uuid import uuid4

import pytest

from aditsystem_backend.models.enums import DocumentoTipo, EntityType
from aditsystem_backend.schemas.documento import DocumentoCreate


def base_payload() -> dict:
    return {
        "entity_type": EntityType.POLITICO,
        "entity_id": uuid4(),
        "tipo": DocumentoTipo.CV,
        "titulo": "CV 2026",
        "s3_key": "politicos/abc/cv/v1.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 102400,
    }


def test_documento_create_accepts_valid_payload() -> None:
    doc = DocumentoCreate(**base_payload())
    assert doc.tipo == DocumentoTipo.CV
    assert doc.size_bytes == 102400


def test_documento_create_requires_s3_key() -> None:
    payload = base_payload()
    del payload["s3_key"]
    with pytest.raises(ValueError):
        DocumentoCreate(**payload)


def test_documento_create_requires_positive_size() -> None:
    payload = base_payload()
    payload["size_bytes"] = 0
    with pytest.raises(ValueError):
        DocumentoCreate(**payload)


def test_documento_create_accepts_all_entity_types() -> None:
    for et in EntityType:
        payload = base_payload()
        payload["entity_type"] = et
        doc = DocumentoCreate(**payload)
        assert doc.entity_type == et


def test_documento_create_accepts_all_tipos() -> None:
    for tipo in DocumentoTipo:
        payload = base_payload()
        payload["tipo"] = tipo
        doc = DocumentoCreate(**payload)
        assert doc.tipo == tipo


def test_documento_create_accepts_optional_descripcion() -> None:
    payload = base_payload()
    payload["descripcion"] = "Versión actualizada"
    doc = DocumentoCreate(**payload)
    assert doc.descripcion == "Versión actualizada"


def test_documento_create_no_descripcion_by_default() -> None:
    doc = DocumentoCreate(**base_payload())
    assert doc.descripcion is None

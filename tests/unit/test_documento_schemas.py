from uuid import uuid4

import pytest

from aditsystem_backend.models.enums import DocumentoTipo
from aditsystem_backend.schemas.documento import PersonaDocumentoCreate


def base_payload() -> dict:
    return {
        "tipo": DocumentoTipo.CV,
        "titulo": "CV 2026",
        "s3_key": "politicos/abc/cv/v1.pdf",
        "mime_type": "application/pdf",
        "size_bytes": 102400,
    }


def test_documento_create_accepts_valid_payload() -> None:
    doc = PersonaDocumentoCreate(**base_payload())
    assert doc.tipo == DocumentoTipo.CV
    assert doc.size_bytes == 102400


def test_documento_create_requires_s3_key() -> None:
    payload = base_payload()
    del payload["s3_key"]
    with pytest.raises(ValueError):
        PersonaDocumentoCreate(**payload)


def test_documento_create_requires_positive_size() -> None:
    payload = base_payload()
    payload["size_bytes"] = 0
    with pytest.raises(ValueError):
        PersonaDocumentoCreate(**payload)


def test_documento_create_accepts_all_tipos() -> None:
    for tipo in DocumentoTipo:
        payload = base_payload()
        payload["tipo"] = tipo
        doc = PersonaDocumentoCreate(**payload)
        assert doc.tipo == tipo


def test_documento_create_accepts_optional_descripcion() -> None:
    payload = base_payload()
    payload["descripcion"] = "Versión actualizada"
    doc = PersonaDocumentoCreate(**payload)
    assert doc.descripcion == "Versión actualizada"


def test_documento_create_no_descripcion_by_default() -> None:
    doc = PersonaDocumentoCreate(**base_payload())
    assert doc.descripcion is None

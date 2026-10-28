from unittest.mock import MagicMock, patch

import pytest

from aditsystem_backend.core.config import Settings
from aditsystem_backend.core.exceptions import DomainError
from uuid import UUID

from aditsystem_backend.models.enums import DocumentoTipo
from aditsystem_backend.services.document_storage import (
    DocumentStorageService,
    assert_object_key_for_persona,
    build_private_object_key,
    sanitize_download_filename,
)


def test_sanitize_download_filename_strips_unsafe_characters() -> None:
    assert sanitize_download_filename('CV / Ada "2026".pdf') == "CV  Ada 2026.pdf"


def test_presigned_get_url_requires_bucket() -> None:
    service = DocumentStorageService(Settings(documents_s3_bucket=""))
    with pytest.raises(DomainError) as exc:
        service.presigned_get_url(
            object_key="private/person/cv.pdf",
            mime_type="application/pdf",
            download_name="Currículum",
        )
    assert exc.value.status_code == 503


@patch("aditsystem_backend.services.document_storage.boto3.client")
def test_presigned_get_url_returns_url(mock_boto_client: MagicMock) -> None:
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://signed.example/cv.pdf"
    mock_boto_client.return_value = s3

    service = DocumentStorageService(
        Settings(documents_s3_bucket="aditsystem-media")
    )
    result = service.presigned_get_url(
        object_key="private/person/cv.pdf",
        mime_type="application/pdf",
        download_name="Currículum",
    )

    assert result.url == "https://signed.example/cv.pdf"
    s3.generate_presigned_url.assert_called_once()
    params = s3.generate_presigned_url.call_args.kwargs["Params"]
    assert params["Bucket"] == "aditsystem-media"
    assert params["Key"] == "private/person/cv.pdf"


def test_build_private_object_key_scopes_to_persona() -> None:
    persona_id = UUID("11111111-1111-4111-8111-111111111111")
    key = build_private_object_key(persona_id, DocumentoTipo.CV, "mi cv.pdf")
    assert key.startswith(f"personas/{persona_id}/cv/")
    assert key.endswith(".pdf")


def test_assert_object_key_for_persona_rejects_foreign_prefix() -> None:
    persona_id = UUID("11111111-1111-4111-8111-111111111111")
    with pytest.raises(DomainError) as exc:
        assert_object_key_for_persona(persona_id, "personas/other/cv/x.pdf")
    assert exc.value.status_code == 400


@patch("aditsystem_backend.services.document_storage.boto3.client")
def test_presigned_put_url_returns_upload_url(mock_boto_client: MagicMock) -> None:
    s3 = MagicMock()
    s3.generate_presigned_url.return_value = "https://signed.example/upload"
    mock_boto_client.return_value = s3

    service = DocumentStorageService(Settings(documents_s3_bucket="aditsystem-media"))
    result = service.presigned_put_url(
        object_key="personas/p1/cv/u/file.pdf",
        mime_type="application/pdf",
        size_bytes=2048,
    )

    assert result.url == "https://signed.example/upload"
    assert result.object_key == "personas/p1/cv/u/file.pdf"
    s3.generate_presigned_url.assert_called_once()
    assert s3.generate_presigned_url.call_args.kwargs["ClientMethod"] == "put_object"

from unittest.mock import MagicMock, patch

import pytest

from aditsystem_backend.core.config import Settings
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.services.document_storage import (
    DocumentStorageService,
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

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import boto3
from botocore.exceptions import ClientError

from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.core.exceptions import DomainError

_FILENAME_UNSAFE = re.compile(r"[^\w\s.-]", re.UNICODE)


@dataclass(frozen=True)
class PresignedDownload:
    url: str
    expires_at: datetime


def sanitize_download_filename(name: str) -> str:
    cleaned = _FILENAME_UNSAFE.sub("", name).strip() or "documento"
    return cleaned[:200]


class DocumentStorageService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def presigned_get_url(
        self,
        *,
        object_key: str,
        mime_type: str,
        download_name: str,
    ) -> PresignedDownload:
        bucket = self.settings.documents_s3_bucket.strip()
        if not bucket:
            raise DomainError(
                "la descarga de documentos no está configurada en este entorno",
                status_code=503,
            )
        expires = self.settings.documents_presigned_url_expires_seconds
        filename = sanitize_download_filename(download_name)
        client = boto3.client("s3")
        try:
            url = client.generate_presigned_url(
                ClientMethod="get_object",
                Params={
                    "Bucket": bucket,
                    "Key": object_key,
                    "ResponseContentDisposition": (
                        f'attachment; filename="{filename}"'
                    ),
                    "ResponseContentType": mime_type,
                },
                ExpiresIn=expires,
            )
        except ClientError as exc:
            raise DomainError(
                "no se pudo preparar la descarga del documento",
                status_code=503,
            ) from exc
        return PresignedDownload(
            url=url,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires),
        )

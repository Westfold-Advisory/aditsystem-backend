from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID

import boto3
from botocore.exceptions import ClientError

from aditsystem_backend.core.config import Settings, get_settings
from aditsystem_backend.core.exceptions import DomainError
from aditsystem_backend.models.enums import DocumentoTipo

_FILENAME_UNSAFE = re.compile(r"[^\w\s.-]", re.UNICODE)
_OBJECT_KEY_UNSAFE = re.compile(r"[^a-zA-Z0-9._/-]")


@dataclass(frozen=True)
class PresignedDownload:
    url: str
    expires_at: datetime


@dataclass(frozen=True)
class PresignedUpload:
    url: str
    object_key: str
    expires_at: datetime
    mime_type: str


def sanitize_download_filename(name: str) -> str:
    cleaned = _FILENAME_UNSAFE.sub("", name).strip() or "documento"
    return cleaned[:200]


def build_private_object_key(
    persona_id: UUID, tipo: DocumentoTipo, file_name: str
) -> str:
    """Private S3 key aligned with the ADITSYSTEM frontend helper."""
    sanitized = _OBJECT_KEY_UNSAFE.sub("_", file_name.strip())[:120] or "archivo"
    unique = uuid.uuid4()
    return f"personas/{persona_id}/{tipo.value.lower()}/{unique}/{sanitized}"


def assert_object_key_for_persona(persona_id: UUID, object_key: str) -> None:
    prefix = f"personas/{persona_id}/"
    if not object_key.startswith(prefix):
        raise DomainError(
            "la clave de almacenamiento no corresponde a esta persona",
            status_code=400,
        )


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

    def presigned_put_url(
        self,
        *,
        object_key: str,
        mime_type: str,
        size_bytes: int,
    ) -> PresignedUpload:
        bucket = self.settings.documents_s3_bucket.strip()
        if not bucket:
            raise DomainError(
                "la carga de documentos no está configurada en este entorno",
                status_code=503,
            )
        max_bytes = self.settings.documents_max_upload_bytes
        if size_bytes <= 0 or size_bytes > max_bytes:
            raise DomainError(
                "el tamaño del archivo excede el límite permitido",
                status_code=400,
            )
        expires = self.settings.documents_presigned_url_expires_seconds
        client = boto3.client("s3")
        try:
            url = client.generate_presigned_url(
                ClientMethod="put_object",
                Params={
                    "Bucket": bucket,
                    "Key": object_key,
                    "ContentType": mime_type,
                    "ContentLength": size_bytes,
                },
                ExpiresIn=expires,
            )
        except ClientError as exc:
            raise DomainError(
                "no se pudo preparar la carga del documento",
                status_code=503,
            ) from exc
        return PresignedUpload(
            url=url,
            object_key=object_key,
            expires_at=datetime.now(UTC) + timedelta(seconds=expires),
            mime_type=mime_type,
        )

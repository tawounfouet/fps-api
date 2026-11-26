from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
from re import Pattern, compile
from typing import Any
from urllib.parse import quote, urlsplit
from uuid import UUID

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from fps_platform.modules.media.application.dto import DeletionAuthorizationId
from fps_platform.modules.media.application.ports import (
    DeleteObjectRequest,
    InspectedObject,
    ObjectHead,
    ResolvePublicUrlRequest,
    SignedUploadIntent,
    UploadIntentRequest,
)
from fps_platform.modules.media.domain.enums import MediaMimeType
from fps_platform.modules.media.domain.exceptions import (
    MediaStoragePermanentError,
    MediaStorageTransientError,
)
from fps_platform.modules.media.domain.value_objects import StorageKey
from fps_platform.shared.domain.clock import Clock

TRANSIENT_ERROR_CODES = frozenset(
    {
        "InternalError",
        "RequestTimeout",
        "SlowDown",
        "ServiceUnavailable",
        "503",
        "500",
        "429",
    }
)
MISSING_ERROR_CODES = frozenset({"404", "NoSuchKey", "NotFound"})
STAGING_KEY_PATTERN: Pattern[str] = compile(
    r"^staging/[A-Za-z0-9][A-Za-z0-9._-]{0,127}/"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
)
MIN_INTENT_TTL_SECONDS = 60
MAX_INTENT_TTL_SECONDS = 300
NIL_UUID = UUID(int=0)


class S3MediaStoragePort:
    def __init__(
        self,
        *,
        bucket: str,
        region: str,
        access_key_id: str,
        secret_access_key: str,
        public_base_url: str,
        clock: Clock,
        endpoint_url: str | None = None,
        force_path_style: bool = False,
        signed_url_ttl_seconds: int = 300,
        request_timeout_seconds: float = 10.0,
        client_factory: Callable[..., Any] | None = None,
    ) -> None:
        self._bucket = bucket
        self._clock = clock
        self._public_base_url = public_base_url.rstrip("/")
        self._signed_url_ttl_seconds = signed_url_ttl_seconds
        client_config = Config(
            connect_timeout=request_timeout_seconds,
            read_timeout=request_timeout_seconds,
            retries={"max_attempts": 3, "mode": "standard"},
            signature_version="s3v4",
        )
        client_kwargs: dict[str, Any] = {
            "service_name": "s3",
            "region_name": region,
            "aws_access_key_id": access_key_id,
            "aws_secret_access_key": secret_access_key,
            "config": client_config,
        }
        if endpoint_url is not None:
            client_kwargs["endpoint_url"] = endpoint_url
        if force_path_style:
            client_kwargs["config"] = Config(
                connect_timeout=request_timeout_seconds,
                read_timeout=request_timeout_seconds,
                retries={"max_attempts": 3, "mode": "standard"},
                signature_version="s3v4",
                s3={"addressing_style": "path"},
            )
        factory = client_factory if client_factory is not None else boto3.client
        self._client = factory(**client_kwargs)

    def create_upload_intent(self, request: UploadIntentRequest) -> SignedUploadIntent:
        key = _validate_staging_key(request.key)
        content_type = _validate_content_type(request.content_type)
        expires_seconds = _validate_ttl(request.expires_seconds)
        if not MIN_INTENT_TTL_SECONDS <= self._signed_url_ttl_seconds <= MAX_INTENT_TTL_SECONDS:
            raise MediaStoragePermanentError("signed URL duration configuration is out of range")
        expires_seconds = min(expires_seconds, self._signed_url_ttl_seconds)
        try:
            url = self._client.generate_presigned_url(
                "put_object",
                Params={
                    "Bucket": self._bucket,
                    "Key": key,
                    "ContentType": content_type,
                },
                ExpiresIn=expires_seconds,
                HttpMethod="PUT",
            )
        except Exception as exc:
            raise self._classify_error(exc, "upload intent could not be created") from None
        expires_at: datetime = self._clock.now() + timedelta(seconds=expires_seconds)
        return SignedUploadIntent(
            method="PUT",
            url=str(url),
            expires_at=expires_at,
            headers={"Content-Type": content_type},
            fields=None,
        )

    def head_object(self, key: StorageKey) -> ObjectHead:
        key_value = _validate_object_key(key)
        try:
            response = self._client.head_object(Bucket=self._bucket, Key=key_value)
        except Exception as exc:
            if self._is_missing(exc):
                return ObjectHead(exists=False)
            raise self._classify_error(exc, "media object head failed") from None
        return ObjectHead(
            exists=True,
            byte_size=self._as_int(response.get("ContentLength")),
            content_type=self._as_optional_str(response.get("ContentType")),
            etag=self._as_optional_str(response.get("ETag")),
        )

    def read_or_inspect_object(self, key: StorageKey, *, max_bytes: int) -> InspectedObject:
        if not isinstance(max_bytes, int) or isinstance(max_bytes, bool) or max_bytes < 1:
            raise MediaStoragePermanentError("inspection limit must be positive")
        key_value = _validate_object_key(key)
        try:
            response = self._client.get_object(
                Bucket=self._bucket,
                Key=key_value,
                Range=f"bytes=0-{max_bytes - 1}",
            )
            body = response["Body"].read(max_bytes)
        except Exception as exc:
            if self._is_missing(exc):
                raise MediaStoragePermanentError("media object does not exist") from None
            raise self._classify_error(exc, "media object inspection failed") from None
        if not isinstance(body, bytes):
            raise MediaStoragePermanentError("media object body is invalid")
        total_size = len(body)
        content_range = response.get("ContentRange")
        if isinstance(content_range, str) and "/" in content_range:
            candidate = content_range.rsplit("/", 1)[-1]
            if candidate.isdigit():
                total_size = int(candidate)
        return InspectedObject(
            body=body,
            byte_size=total_size,
            content_type=self._as_optional_str(response.get("ContentType")),
            etag=self._as_optional_str(response.get("ETag")),
            truncated=total_size > len(body),
        )

    def copy_object(self, *, source_key: StorageKey, destination_key: StorageKey) -> None:
        source = _validate_object_key(source_key)
        destination = _validate_object_key(destination_key)
        if not self.head_object(source_key).exists:
            raise MediaStoragePermanentError("media source object does not exist")
        if self.head_object(destination_key).exists:
            raise MediaStoragePermanentError("media destination object already exists")
        try:
            self._client.copy_object(
                Bucket=self._bucket,
                CopySource={"Bucket": self._bucket, "Key": source},
                Key=destination,
            )
        except Exception as exc:
            if self._is_missing(exc):
                raise MediaStoragePermanentError("media source object does not exist") from None
            raise self._classify_error(exc, "media object copy failed") from None
        if not self.head_object(destination_key).exists:
            raise MediaStoragePermanentError("media destination object was not promoted")

    def delete_object(self, request: DeleteObjectRequest) -> None:
        key = _validate_delete_request(request)
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            raise self._classify_error(exc, "media object delete failed") from None

    def resolve_public_url(self, request: ResolvePublicUrlRequest) -> str:
        key = _validate_resolve_request(request)
        _validate_public_base_url(self._public_base_url)
        return f"{self._public_base_url}/{quote(key, safe='/')}"

    def close(self) -> None:
        return None

    @staticmethod
    def _is_missing(exc: Exception) -> bool:
        if not isinstance(exc, ClientError):
            return False
        code = str(exc.response.get("Error", {}).get("Code", ""))
        return code in MISSING_ERROR_CODES

    @staticmethod
    def _classify_error(
        exc: Exception, message: str
    ) -> MediaStoragePermanentError | MediaStorageTransientError:
        if isinstance(exc, ClientError):
            code = str(exc.response.get("Error", {}).get("Code", ""))
            if code in TRANSIENT_ERROR_CODES:
                return MediaStorageTransientError(message)
        elif isinstance(exc, BotoCoreError):
            return MediaStorageTransientError(message)
        return MediaStoragePermanentError(message)

    @staticmethod
    def _as_optional_str(value: object) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _as_int(value: object) -> int | None:
        return value if isinstance(value, int) and not isinstance(value, bool) else None


def _validate_staging_key(key: object) -> str:
    value = str(key)
    if ".." in value or value.startswith("/") or not value.isascii():
        raise MediaStoragePermanentError("upload intent key is not a server-generated staging key")
    if not STAGING_KEY_PATTERN.fullmatch(value):
        raise MediaStoragePermanentError("upload intent key is not a server-generated staging key")
    nonce = value.rsplit("/", 1)[-1]
    try:
        parsed = UUID(nonce)
    except ValueError:
        raise MediaStoragePermanentError(
            "upload intent key is not a server-generated staging key"
        ) from None
    if str(parsed) != nonce.lower() or parsed == NIL_UUID:
        raise MediaStoragePermanentError("upload intent key is not a server-generated staging key")
    return value


def _validate_content_type(content_type: object) -> str:
    value = str(content_type)
    try:
        MediaMimeType(value)
    except ValueError:
        raise MediaStoragePermanentError("upload intent content type is not supported") from None
    return value


def _validate_ttl(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise MediaStoragePermanentError("upload intent duration is out of range")
    if not MIN_INTENT_TTL_SECONDS <= value <= MAX_INTENT_TTL_SECONDS:
        raise MediaStoragePermanentError("upload intent duration is out of range")
    return value


def _validate_object_key(key: object) -> str:
    value = str(key)
    if (
        not value
        or not value.isascii()
        or ".." in value
        or value.startswith("/")
        or value.endswith("/")
        or "//" in value
        or any(character.isspace() for character in value)
    ):
        raise MediaStoragePermanentError("media key is not usable")
    return value


def _validate_delete_request(request: DeleteObjectRequest) -> str:
    key = _validate_object_key(request.key)
    authorization = getattr(request, "authorized_deletion_id", None)
    if (
        not isinstance(authorization, DeletionAuthorizationId)
        or not isinstance(authorization.value, UUID)
        or authorization.value == NIL_UUID
    ):
        raise MediaStoragePermanentError("deletion is not authorized")
    return key


def _validate_resolve_request(request: ResolvePublicUrlRequest) -> str:
    key = _validate_object_key(request.key)
    proof = getattr(request, "readiness_proof_id", None)
    if not isinstance(proof, UUID) or proof == NIL_UUID:
        raise MediaStoragePermanentError("readiness proof is missing")
    return key


def _validate_public_base_url(public_base_url: str) -> None:
    parsed = urlsplit(public_base_url)
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.query
        or parsed.fragment
    ):
        raise MediaStoragePermanentError("public base URL is not usable")

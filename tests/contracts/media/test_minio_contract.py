from __future__ import annotations

import os
import socket
from datetime import UTC, datetime
from urllib.parse import urlsplit
from urllib.request import Request, urlopen
from uuid import uuid4

import pytest

from fps_platform.modules.media.application.dto import DeletionAuthorizationId
from fps_platform.modules.media.application.ports import (
    DeleteObjectRequest,
    ResolvePublicUrlRequest,
    UploadIntentRequest,
)
from fps_platform.modules.media.domain.enums import MediaMimeType
from fps_platform.modules.media.domain.exceptions import MediaStoragePermanentError
from fps_platform.modules.media.domain.value_objects import MimeType, StorageKey
from fps_platform.modules.media.infrastructure.s3_storage import S3MediaStoragePort
from fps_platform.shared.domain.clock import FakeClock

SYNTHETIC_BUCKET = "fps-media-contract"
SYNTHETIC_REGION = "local"
SYNTHETIC_ACCESS_KEY = "minio-contract-access"
SYNTHETIC_SECRET_KEY = "minio-contract-secret"
SYNTHETIC_PUBLIC_BASE_URL = "https://media.example.test"
PAYLOAD = b"minio-contract-payload"


def endpoint_is_reachable(endpoint_url: str) -> bool:
    parsed = urlsplit(endpoint_url)
    if parsed.hostname is None:
        return False
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    try:
        with socket.create_connection((parsed.hostname, port), timeout=2):
            return True
    except OSError:
        return False


def run_storage_contract(
    *,
    endpoint_url: str,
    bucket: str,
    region: str,
    access_key_id: str,
    secret_access_key: str,
    public_base_url: str = SYNTHETIC_PUBLIC_BASE_URL,
) -> None:
    port = S3MediaStoragePort(
        bucket=bucket,
        region=region,
        access_key_id=access_key_id,
        secret_access_key=secret_access_key,
        public_base_url=public_base_url,
        clock=FakeClock(datetime(2026, 11, 26, 12, tzinfo=UTC)),
        endpoint_url=endpoint_url,
        force_path_style=True,
        signed_url_ttl_seconds=300,
        request_timeout_seconds=10.0,
    )
    run_id = uuid4().hex
    staging_key = StorageKey(f"staging/{run_id}/{uuid4()}")
    final_key = StorageKey(f"media/{run_id}/{uuid4().hex}/original")
    intent = port.create_upload_intent(
        UploadIntentRequest(
            key=staging_key,
            content_type=MimeType(MediaMimeType.PNG),
            expires_seconds=300,
        )
    )
    assert intent.method == "PUT"
    assert intent.headers == {"Content-Type": "image/png"}
    put_request = Request(
        intent.url,
        data=PAYLOAD,
        method="PUT",
        headers={"Content-Type": "image/png"},
    )
    with urlopen(put_request, timeout=10) as response:
        assert response.status < 300
    assert port.head_object(staging_key).byte_size == len(PAYLOAD)
    inspected = port.read_or_inspect_object(staging_key, max_bytes=4)
    assert inspected.body == PAYLOAD[:4]
    assert inspected.byte_size == len(PAYLOAD)

    port.copy_object(source_key=staging_key, destination_key=final_key)
    assert port.head_object(final_key).exists
    with pytest.raises(MediaStoragePermanentError):
        port.copy_object(source_key=staging_key, destination_key=final_key)

    url = port.resolve_public_url(ResolvePublicUrlRequest(final_key, uuid4()))
    assert url.startswith(f"{public_base_url}/")
    assert "?" not in url and "#" not in url
    assert access_key_id not in url and secret_access_key not in url

    port.delete_object(DeleteObjectRequest(final_key, DeletionAuthorizationId(uuid4())))
    assert not port.head_object(final_key).exists
    port.delete_object(DeleteObjectRequest(staging_key, DeletionAuthorizationId(uuid4())))
    port.close()


def test_minio_storage_contract() -> None:
    endpoint_url = os.environ.get("FPS_MEDIA_ENDPOINT_URL")
    if not endpoint_url:
        pytest.skip("NOT_EXECUTED: FPS_MEDIA_ENDPOINT_URL is not set")
    if not endpoint_is_reachable(endpoint_url):
        pytest.skip("NOT_EXECUTED: MinIO endpoint is not reachable")
    run_storage_contract(
        endpoint_url=endpoint_url,
        bucket=SYNTHETIC_BUCKET,
        region=SYNTHETIC_REGION,
        access_key_id=SYNTHETIC_ACCESS_KEY,
        secret_access_key=SYNTHETIC_SECRET_KEY,
    )

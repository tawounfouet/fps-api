from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime, timedelta
from io import BytesIO
from typing import Any
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from fps_platform.modules.media.application.dto import DeletionAuthorizationId
from fps_platform.modules.media.application.ports import (
    DeleteObjectRequest,
    ResolvePublicUrlRequest,
    UploadIntentRequest,
)
from fps_platform.modules.media.domain.enums import MediaMimeType
from fps_platform.modules.media.domain.exceptions import (
    MediaStoragePermanentError,
    MediaStorageTransientError,
)
from fps_platform.modules.media.domain.value_objects import MimeType, StorageKey
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.modules.media.infrastructure.s3_storage import S3MediaStoragePort
from fps_platform.shared.domain.clock import FakeClock

MOMENT = datetime(2026, 11, 25, 12, 0, tzinfo=UTC)
STAGING_KEY = StorageKey("staging/intent-001/3f2504e0-4f89-41d3-9a0c-0305e82c3301")
FINAL_KEY = StorageKey("media/2026/11/asset/original.png")
REQUEST = UploadIntentRequest(
    key=STAGING_KEY,
    content_type=MimeType(MediaMimeType.PNG),
    expires_seconds=300,
)
DELETE_REQUEST = DeleteObjectRequest(
    key=FINAL_KEY,
    authorized_deletion_id=DeletionAuthorizationId(uuid4()),
)
URL_REQUEST = ResolvePublicUrlRequest(key=FINAL_KEY, readiness_proof_id=uuid4())


class FakeS3Client:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.deleted: list[str] = []
        self.copy_calls: list[tuple[str, str]] = []
        self.presign_params: dict[str, Any] = {}
        self.presign_expires_in: int | None = None

    def generate_presigned_url(
        self,
        operation: str,
        *,
        Params: dict[str, Any],
        ExpiresIn: int,
        HttpMethod: str,
    ) -> str:
        assert operation == "put_object"
        assert HttpMethod == "PUT"
        self.presign_params = dict(Params)
        self.presign_expires_in = ExpiresIn
        return "https://storage.test/signed-upload"

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        body = self.objects.get(Key)
        if body is None:
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "HeadObject")
        return {
            "ContentLength": len(body),
            "ContentType": "image/png",
            "ETag": '"abc123"',
        }

    def get_object(self, *, Bucket: str, Key: str, Range: str) -> dict[str, Any]:
        body = self.objects.get(Key)
        if body is None:
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "GetObject")
        limit = int(Range.removeprefix("bytes=0-")) + 1
        return {
            "Body": BytesIO(body[:limit]),
            "ContentRange": f"bytes 0-{min(limit, len(body)) - 1}/{len(body)}",
            "ContentType": "image/png",
            "ETag": '"abc123"',
        }

    def copy_object(self, *, Bucket: str, CopySource: dict[str, str], Key: str) -> None:
        body = self.objects.get(CopySource["Key"])
        if body is None:
            raise ClientError({"Error": {"Code": "404", "Message": "missing"}}, "CopyObject")
        if Key in self.objects:
            raise ClientError({"Error": {"Code": "412", "Message": "exists"}}, "CopyObject")
        self.copy_calls.append((CopySource["Key"], Key))
        self.objects[Key] = body

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        self.objects.pop(Key, None)
        self.deleted.append(Key)


def make_fake_port() -> InMemoryMediaStoragePort:
    port = InMemoryMediaStoragePort(FakeClock(MOMENT), public_base_url="https://media.test")
    port.put_object(STAGING_KEY, b"0123456789", "image/png")
    return port


def make_s3_port(client: FakeS3Client) -> S3MediaStoragePort:
    return S3MediaStoragePort(
        bucket="fps-media-test",
        region="local",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        public_base_url="https://media.test",
        clock=FakeClock(MOMENT),
        endpoint_url="http://minio:9000",
        force_path_style=True,
        client_factory=lambda **_: client,
    )


def test_fake_adapter_contract() -> None:
    port = make_fake_port()
    intent = port.create_upload_intent(REQUEST)
    assert intent.method == "PUT"
    assert intent.expires_at == MOMENT + timedelta(seconds=300)
    assert intent.headers == {"Content-Type": "image/png"}
    head = port.head_object(STAGING_KEY)
    assert head.exists and head.byte_size == 10
    inspected = port.read_or_inspect_object(STAGING_KEY, max_bytes=4)
    assert inspected.body == b"0123"
    assert inspected.byte_size == 10
    assert inspected.truncated
    port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)
    assert port.head_object(FINAL_KEY).exists
    assert (
        port.resolve_public_url(URL_REQUEST)
        == "https://media.test/media/2026/11/asset/original.png"
    )
    port.delete_object(DELETE_REQUEST)
    assert not port.head_object(FINAL_KEY).exists
    port.close()


def test_s3_adapter_contract_uses_signed_staging_key() -> None:
    client = FakeS3Client()
    client.objects[str(STAGING_KEY)] = b"0123456789"
    port = make_s3_port(client)
    intent = port.create_upload_intent(REQUEST)
    assert intent.url == "https://storage.test/signed-upload"
    assert intent.expires_at == MOMENT + timedelta(seconds=300)
    assert client.presign_params["ContentType"] == "image/png"
    assert client.presign_expires_in == 300
    assert port.head_object(StorageKey("staging/intent-001/missing")).exists is False
    inspected = port.read_or_inspect_object(STAGING_KEY, max_bytes=4)
    assert inspected.body == b"0123"
    assert inspected.byte_size == 10
    assert inspected.truncated
    port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)
    assert port.head_object(FINAL_KEY).byte_size == 10
    assert (
        port.resolve_public_url(URL_REQUEST)
        == "https://media.test/media/2026/11/asset/original.png"
    )
    port.delete_object(DELETE_REQUEST)
    assert str(FINAL_KEY) in client.deleted
    port.close()


def test_upload_intent_ttl_cannot_exceed_300_seconds() -> None:
    over_limit = replace(REQUEST, expires_seconds=301)
    with pytest.raises(MediaStoragePermanentError):
        make_fake_port().create_upload_intent(over_limit)
    with pytest.raises(MediaStoragePermanentError):
        make_s3_port(FakeS3Client()).create_upload_intent(over_limit)


def test_s3_adapter_classifies_transient_errors() -> None:
    class FailingClient(FakeS3Client):
        def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
            raise ClientError({"Error": {"Code": "503", "Message": "busy"}}, "HeadObject")

    port = make_s3_port(FailingClient())
    with pytest.raises(MediaStorageTransientError) as exc_info:
        port.head_object(STAGING_KEY)
    assert exc_info.value.retryable is True

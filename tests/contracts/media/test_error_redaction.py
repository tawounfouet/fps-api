from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, cast
from uuid import uuid4

import pytest
from botocore.exceptions import ClientError

from fps_platform.modules.media.application.dto import DeletionAuthorizationId
from fps_platform.modules.media.application.ports import (
    DeleteObjectRequest,
    UploadIntentRequest,
)
from fps_platform.modules.media.domain.exceptions import (
    MediaStorageError,
    MediaStoragePermanentError,
    MediaStorageTransientError,
)
from fps_platform.modules.media.domain.value_objects import MimeType, StorageKey

from .test_storage_port import STAGING_KEY, FakeS3Client, make_s3_port

LEAK_PAYLOAD = (
    "https://storage.test/signed-upload?X-Amz-Signature=deadbeef "
    "fps-media-test http://minio:9000 test-access-key test-secret-key"
)


@dataclass(slots=True)
class RawKey:
    value: str

    def __str__(self) -> str:
        return self.value


def leaking_error(code: str, operation: str) -> ClientError:
    return ClientError({"Error": {"Code": code, "Message": LEAK_PAYLOAD}}, operation)


class LeakingClient(FakeS3Client):
    def generate_presigned_url(
        self,
        operation: str,
        *,
        Params: dict[str, Any],
        ExpiresIn: int,
        HttpMethod: str,
    ) -> str:
        raise leaking_error("403", "Presign")

    def head_object(self, *, Bucket: str, Key: str) -> dict[str, Any]:
        raise leaking_error("503", "HeadObject")

    def get_object(self, *, Bucket: str, Key: str, Range: str) -> dict[str, Any]:
        raise leaking_error("503", "GetObject")

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        raise leaking_error("503", "DeleteObject")


class LeakingCopyClient(FakeS3Client):
    def copy_object(self, *, Bucket: str, CopySource: dict[str, str], Key: str) -> None:
        raise leaking_error("500", "CopyObject")


def assert_redacted(exc: BaseException, caplog: pytest.LogCaptureFixture) -> None:
    message = str(exc)
    for token in (
        "signed-upload",
        "X-Amz-Signature",
        "deadbeef",
        "fps-media-test",
        "minio:9000",
        "test-access-key",
        "test-secret-key",
    ):
        assert token.lower() not in message.lower()
        assert token.lower() not in caplog.text.lower()
    assert exc.__cause__ is None


def test_provider_errors_are_redacted_and_classified(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    port = make_s3_port(LeakingClient())
    with pytest.raises(MediaStorageTransientError) as head_exc:
        port.head_object(STAGING_KEY)
    assert head_exc.value.retryable is True
    assert_redacted(head_exc.value, caplog)

    with pytest.raises(MediaStorageTransientError) as inspect_exc:
        port.read_or_inspect_object(STAGING_KEY, max_bytes=4)
    assert inspect_exc.value.retryable is True
    assert_redacted(inspect_exc.value, caplog)

    delete_request = DeleteObjectRequest(STAGING_KEY, DeletionAuthorizationId(uuid4()))
    with pytest.raises(MediaStorageTransientError) as delete_exc:
        port.delete_object(delete_request)
    assert delete_exc.value.retryable is True
    assert_redacted(delete_exc.value, caplog)


def test_presign_error_is_redacted(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    port = make_s3_port(LeakingClient())
    request = UploadIntentRequest(
        key=STAGING_KEY,
        content_type=MimeType("image/png"),
        expires_seconds=300,
    )
    with pytest.raises(MediaStoragePermanentError) as exc_info:
        port.create_upload_intent(request)
    assert exc_info.value.retryable is False
    assert_redacted(exc_info.value, caplog)


def test_copy_provider_error_is_redacted(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    client = LeakingCopyClient()
    client.objects[str(STAGING_KEY)] = b"bytes"
    port = make_s3_port(client)
    with pytest.raises(MediaStorageTransientError) as exc_info:
        port.copy_object(source_key=STAGING_KEY, destination_key=StorageKey("media/final/original"))
    assert exc_info.value.retryable is True
    assert_redacted(exc_info.value, caplog)


def test_validation_errors_do_not_echo_keys(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.DEBUG)
    port = make_s3_port(FakeS3Client())
    with pytest.raises(MediaStoragePermanentError) as exc_info:
        port.head_object(cast(StorageKey, RawKey("media/final/secret marker")))
    assert "secret-marker" not in str(exc_info.value)
    assert "secret-marker" not in caplog.text


def test_storage_error_classes_keep_retryable_flag() -> None:
    transient = MediaStorageTransientError("message")
    permanent = MediaStoragePermanentError("message")
    assert isinstance(transient, MediaStorageError)
    assert isinstance(permanent, MediaStorageError)
    assert transient.retryable is True
    assert permanent.retryable is False

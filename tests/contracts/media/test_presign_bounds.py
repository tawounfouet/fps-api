from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, cast

import pytest

from fps_platform.modules.media.application.ports import UploadIntentRequest
from fps_platform.modules.media.domain.exceptions import MediaStoragePermanentError
from fps_platform.modules.media.domain.value_objects import MimeType, StorageKey

from .test_storage_port import (
    MOMENT,
    STAGING_KEY,
    FakeS3Client,
    make_fake_port,
    make_s3_port,
)

VALID_NONCE = "3f2504e0-4f89-41d3-9a0c-0305e82c3301"
INVALID_KEYS = (
    "media/2026/11/asset/original.png",
    "staging/intent-001/nonce-client-controlled",
    "staging/intent-001/../final/original.png",
    f"/staging/intent-001/{VALID_NONCE}",
    f"staging/intent-001/caf\u00e9-{VALID_NONCE}",
    f"staging/intent-001/\u202e{VALID_NONCE}",
    "staging/intent-001/00000000-0000-0000-0000-000000000000",
)


@dataclass(slots=True)
class RawKey:
    value: str

    def __str__(self) -> str:
        return self.value


@dataclass(slots=True)
class RawContentType:
    value: str

    def __str__(self) -> str:
        return self.value


def request_for(
    key: object, *, ttl: int = 300, content_type: object | None = None
) -> UploadIntentRequest:
    return UploadIntentRequest(
        key=cast(StorageKey, key),
        content_type=cast(
            MimeType, content_type if content_type is not None else MimeType("image/png")
        ),
        expires_seconds=ttl,
    )


def fake_bundle() -> Any:
    return make_fake_port(), None


def s3_bundle() -> Any:
    client = FakeS3Client()
    return make_s3_port(client), client


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
@pytest.mark.parametrize("key", INVALID_KEYS)
def test_upload_intent_rejects_client_and_unsafe_keys(bundle_factory: Any, key: str) -> None:
    port, _ = bundle_factory()
    with pytest.raises(MediaStoragePermanentError, match="staging key"):
        port.create_upload_intent(request_for(RawKey(key)))


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_upload_intent_rejects_out_of_range_ttl(bundle_factory: Any) -> None:
    port, _ = bundle_factory()
    for ttl in (0, 59, 301, 3600):
        with pytest.raises(MediaStoragePermanentError, match="duration"):
            port.create_upload_intent(request_for(STAGING_KEY, ttl=ttl))


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
@pytest.mark.parametrize("ttl", [60, 300])
def test_upload_intent_ttl_bounds_are_inclusive(bundle_factory: Any, ttl: int) -> None:
    port, client = bundle_factory()
    intent = port.create_upload_intent(request_for(STAGING_KEY, ttl=ttl))
    assert intent.expires_at == MOMENT + timedelta(seconds=ttl)
    assert intent.method == "PUT"
    if client is not None:
        assert client.presign_expires_in == ttl


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_upload_intent_signs_put_method_and_content_type(bundle_factory: Any) -> None:
    port, client = bundle_factory()
    intent = port.create_upload_intent(request_for(STAGING_KEY))
    assert intent.method == "PUT"
    assert intent.headers == {"Content-Type": "image/png"}
    assert intent.fields is None
    if client is not None:
        assert client.presign_params["Key"] == str(STAGING_KEY)
        assert client.presign_params["ContentType"] == "image/png"
    else:
        assert str(STAGING_KEY) in intent.url
        assert "image%2Fpng" not in intent.url


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_upload_intent_rejects_unsupported_content_type(bundle_factory: Any) -> None:
    port, _ = bundle_factory()
    with pytest.raises(MediaStoragePermanentError, match="content type"):
        port.create_upload_intent(
            request_for(STAGING_KEY, content_type=RawContentType("text/html"))
        )


def test_server_generated_staging_key_is_accepted() -> None:
    key = StorageKey(f"staging/intent-001/{VALID_NONCE}")
    port = make_fake_port()
    intent = port.create_upload_intent(request_for(key))
    assert str(key) in intent.url

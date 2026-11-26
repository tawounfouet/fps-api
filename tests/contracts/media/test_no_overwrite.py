from __future__ import annotations

from typing import Any

import pytest

from fps_platform.modules.media.application.ports import MediaStoragePort
from fps_platform.modules.media.domain.exceptions import MediaStoragePermanentError
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.modules.media.infrastructure.s3_storage import S3MediaStoragePort
from fps_platform.shared.domain.clock import FakeClock

from .test_storage_port import (
    FINAL_KEY,
    MOMENT,
    STAGING_KEY,
    FakeS3Client,
    make_fake_port,
    make_s3_port,
)

FINAL_BODY = b"final-original-bytes"
STAGING_BODY = b"staging-bytes"


def fake_bundle() -> tuple[MediaStoragePort, FakeS3Client | None, InMemoryMediaStoragePort | None]:
    fake = InMemoryMediaStoragePort(FakeClock(MOMENT), public_base_url="https://media.test")
    return fake, None, fake


def s3_bundle() -> tuple[MediaStoragePort, FakeS3Client | None, InMemoryMediaStoragePort | None]:
    client = FakeS3Client()
    return make_s3_port(client), client, None


def seed_final(
    client: FakeS3Client | None, fake: InMemoryMediaStoragePort | None, body: bytes
) -> None:
    if client is not None:
        client.objects[str(FINAL_KEY)] = body
    elif fake is not None:
        fake.put_object(FINAL_KEY, body, "image/png")


def read_final(
    port: MediaStoragePort, client: FakeS3Client | None, fake: InMemoryMediaStoragePort | None
) -> bytes:
    if client is not None:
        return client.objects[str(FINAL_KEY)]
    assert fake is not None
    return fake.read_or_inspect_object(FINAL_KEY, max_bytes=128).body


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_copy_refuses_existing_destination(
    bundle_factory: Any,
) -> None:
    port, client, fake = bundle_factory()
    seed_final(client, fake, FINAL_BODY)
    if client is not None:
        client.objects[str(STAGING_KEY)] = STAGING_BODY
    elif fake is not None:
        fake.put_object(STAGING_KEY, STAGING_BODY, "image/png")
    with pytest.raises(MediaStoragePermanentError, match="already exists") as exc_info:
        port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)
    assert exc_info.value.retryable is False
    assert read_final(port, client, fake) == FINAL_BODY
    if client is not None:
        assert client.copy_calls == []


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_second_copy_is_refused_without_touching_destination(bundle_factory: Any) -> None:
    port, client, fake = bundle_factory()
    if client is not None:
        client.objects[str(STAGING_KEY)] = STAGING_BODY
    elif fake is not None:
        fake.put_object(STAGING_KEY, STAGING_BODY, "image/png")
    port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)
    assert read_final(port, client, fake) == STAGING_BODY
    with pytest.raises(MediaStoragePermanentError, match="already exists"):
        port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)
    assert read_final(port, client, fake) == STAGING_BODY
    if client is not None:
        assert len(client.copy_calls) == 1


def test_staging_reput_after_promotion_does_not_modify_final() -> None:
    port = make_fake_port()
    port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)
    port.put_object(STAGING_KEY, b"reused-staging-upload", "image/png")
    assert port.read_or_inspect_object(FINAL_KEY, max_bytes=128).body == b"0123456789"
    with pytest.raises(MediaStoragePermanentError, match="already exists"):
        port.put_object(FINAL_KEY, b"overwrite", "image/png")
    assert port.read_or_inspect_object(FINAL_KEY, max_bytes=128).body == b"0123456789"


def test_copy_post_head_proof_failure_is_detected() -> None:
    class LosingClient(FakeS3Client):
        def copy_object(self, *, Bucket: str, CopySource: dict[str, str], Key: str) -> None:
            super().copy_object(Bucket=Bucket, CopySource=CopySource, Key=Key)
            self.objects.pop(Key, None)

    client = LosingClient()
    client.objects[str(STAGING_KEY)] = STAGING_BODY
    port = make_s3_port(client)
    with pytest.raises(MediaStoragePermanentError, match="was not promoted"):
        port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_copy_missing_source_is_permanent(bundle_factory: Any) -> None:
    port, _, _ = bundle_factory()
    with pytest.raises(MediaStoragePermanentError, match="source object does not exist"):
        port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)


def test_s3_adapter_does_not_rely_on_provider_overwrite() -> None:
    client = FakeS3Client()
    client.objects[str(STAGING_KEY)] = STAGING_BODY
    port: S3MediaStoragePort = make_s3_port(client)
    port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)
    with pytest.raises(MediaStoragePermanentError):
        port.copy_object(source_key=STAGING_KEY, destination_key=FINAL_KEY)
    assert client.objects[str(FINAL_KEY)] == STAGING_BODY

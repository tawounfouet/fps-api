from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from typing import Any
from uuid import UUID, uuid4

import pytest

from fps_platform.modules.media.application.dto import DeletionAuthorizationId
from fps_platform.modules.media.application.ports import (
    DeleteObjectRequest,
    ResolvePublicUrlRequest,
)
from fps_platform.modules.media.domain.exceptions import MediaStoragePermanentError
from fps_platform.modules.media.infrastructure.fake_storage import InMemoryMediaStoragePort
from fps_platform.modules.media.infrastructure.s3_storage import S3MediaStoragePort
from fps_platform.shared.domain.clock import FakeClock

from .test_storage_port import FINAL_KEY, FakeS3Client, make_fake_port, make_s3_port

NIL_UUID = UUID(int=0)
SENSITIVE_TOKENS = ("fps-media-test", "minio:9000", "test-access-key", "test-secret-key", "X-Amz")


def fake_bundle() -> Any:
    port = make_fake_port()
    return port, None, port


def s3_bundle() -> Any:
    client = FakeS3Client()
    return make_s3_port(client), client, None


def delete_request(authorization: object) -> Any:
    return SimpleNamespace(key=FINAL_KEY, authorized_deletion_id=authorization)


def resolve_request(proof: object) -> Any:
    return SimpleNamespace(key=FINAL_KEY, readiness_proof_id=proof)


def seed_final(client: FakeS3Client | None, fake: InMemoryMediaStoragePort | None) -> None:
    if client is not None:
        client.objects[str(FINAL_KEY)] = b"final-bytes"
    elif fake is not None:
        fake.put_object(FINAL_KEY, b"final-bytes", "image/png")


def final_exists(client: FakeS3Client | None, port: Any) -> bool:
    if client is not None:
        return str(FINAL_KEY) in client.objects
    return bool(port.head_object(FINAL_KEY).exists)


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
@pytest.mark.parametrize(
    "authorization",
    [None, "authorization", NIL_UUID, DeletionAuthorizationId(NIL_UUID)],
)
def test_delete_requires_authorized_deletion_id(bundle_factory: Any, authorization: object) -> None:
    port, client, fake = bundle_factory()
    seed_final(client, fake)
    with pytest.raises(MediaStoragePermanentError, match="not authorized"):
        port.delete_object(delete_request(authorization))
    assert final_exists(client, port)


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_delete_without_authorization_field_is_refused(bundle_factory: Any) -> None:
    port, _, _ = bundle_factory()
    with pytest.raises(MediaStoragePermanentError, match="not authorized"):
        port.delete_object(SimpleNamespace(key=FINAL_KEY))


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_authorized_delete_removes_object(bundle_factory: Any) -> None:
    port, client, fake = bundle_factory()
    seed_final(client, fake)
    request = DeleteObjectRequest(FINAL_KEY, DeletionAuthorizationId(uuid4()))
    port.delete_object(request)
    assert not final_exists(client, port)


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
@pytest.mark.parametrize("proof", [None, "ready", NIL_UUID])
def test_resolve_requires_readiness_proof(bundle_factory: Any, proof: object) -> None:
    port, _, _ = bundle_factory()
    with pytest.raises(MediaStoragePermanentError, match="readiness proof"):
        port.resolve_public_url(resolve_request(proof))


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_resolve_without_proof_field_is_refused(bundle_factory: Any) -> None:
    port, _, _ = bundle_factory()
    with pytest.raises(MediaStoragePermanentError, match="readiness proof"):
        port.resolve_public_url(SimpleNamespace(key=FINAL_KEY))


@pytest.mark.parametrize("bundle_factory", [fake_bundle, s3_bundle], ids=["fake", "s3"])
def test_resolve_public_url_contains_no_provider_material(bundle_factory: Any) -> None:
    port, _, _ = bundle_factory()
    request = ResolvePublicUrlRequest(FINAL_KEY, uuid4())
    url = port.resolve_public_url(request)
    assert url == "https://media.test/media/2026/11/asset/original.png"
    assert "?" not in url and "#" not in url
    for token in SENSITIVE_TOKENS:
        assert token.lower() not in url.lower()


def test_bad_public_base_url_is_refused_without_leaking_material() -> None:
    bad_base_url = "https://user:synthetic-password@media.test/base?X-Amz-Signature=token"
    fake = InMemoryMediaStoragePort(
        FakeClock(datetime(2026, 11, 26, 12, tzinfo=UTC)), public_base_url=bad_base_url
    )
    s3 = S3MediaStoragePort(
        bucket="fps-media-test",
        region="local",
        access_key_id="test-access-key",
        secret_access_key="test-secret-key",
        public_base_url=bad_base_url,
        clock=FakeClock(datetime(2026, 11, 26, 12, tzinfo=UTC)),
        client_factory=lambda **_: FakeS3Client(),
    )
    request = ResolvePublicUrlRequest(FINAL_KEY, uuid4())
    for port in (fake, s3):
        with pytest.raises(MediaStoragePermanentError) as exc_info:
            port.resolve_public_url(request)
        for token in ("synthetic-password", "X-Amz-Signature", "fps-media-test"):
            assert token.lower() not in str(exc_info.value).lower()

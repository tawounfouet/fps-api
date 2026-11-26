from __future__ import annotations

from inspect import signature
from pathlib import Path

from fps_platform.modules.media.application import ports
from fps_platform.modules.media.application.dto import DeletionAuthorizationId, MediaErrorCode
from fps_platform.modules.media.domain.enums import MediaCoverageStatus
from fps_platform.modules.media.domain.value_objects import MAX_UPLOAD_ATTEMPTS

ROOT = Path(__file__).resolve().parents[3] / "src" / "fps_platform" / "modules" / "media"
FORBIDDEN_TOKENS = ("boto3", "botocore", "fastapi", "sqlalchemy")


def _protected_sources() -> list[Path]:
    domain = ROOT / "domain"
    return [*domain.glob("*.py"), ROOT / "application" / "dto.py"]


def test_domain_and_dto_do_not_import_transport_or_persistence_sdks() -> None:
    for path in _protected_sources():
        lowered = path.read_text(encoding="utf-8").lower()
        for token in FORBIDDEN_TOKENS:
            assert token not in lowered, f"{path.name} must not import {token}"


def test_storage_port_signatures_are_explicit() -> None:
    assert list(signature(ports.MediaStoragePort.delete_object).parameters) == ["self", "request"]
    assert list(signature(ports.MediaStoragePort.resolve_public_url).parameters) == [
        "self",
        "request",
    ]
    assert list(signature(ports.MediaStoragePort.read_or_inspect_object).parameters) == [
        "self",
        "key",
        "max_bytes",
    ]
    assert list(signature(ports.MediaStoragePort.copy_object).parameters) == [
        "self",
        "source_key",
        "destination_key",
    ]
    assert hasattr(ports.MediaStoragePort, "close")
    assert hasattr(ports, "ImageInspectionPort")
    assert list(signature(ports.ImageInspectionPort.inspect).parameters) == [
        "self",
        "body",
        "content_type",
    ]


def test_request_objects_carry_authorization_and_proof() -> None:
    assert [field.name for field in ports.DeleteObjectRequest.__dataclass_fields__.values()] == [
        "key",
        "authorized_deletion_id",
    ]
    assert [
        field.name for field in ports.ResolvePublicUrlRequest.__dataclass_fields__.values()
    ] == [
        "key",
        "readiness_proof_id",
    ]
    assert DeletionAuthorizationId.__name__ == "DeletionAuthorizationId"
    assert MAX_UPLOAD_ATTEMPTS == 3
    assert MediaCoverageStatus.PARTIAL == "PARTIAL"
    assert set(MediaErrorCode) == {
        MediaErrorCode.MEDIA_TOO_LARGE,
        MediaErrorCode.UNSUPPORTED_MEDIA_TYPE,
        MediaErrorCode.MEDIA_CORRUPT,
        MediaErrorCode.STORAGE_TEMPORARY_FAILURE,
        MediaErrorCode.MEDIA_STILL_IN_USE,
    }

from __future__ import annotations

from pathlib import Path

import pytest

from fps_platform.modules.media.application.dto import MediaErrorCode
from fps_platform.modules.media.application.services.promotion import (
    ImageInspectionPolicy,
    MediaInspectionError,
)
from fps_platform.modules.media.infrastructure.image_inspection import PillowImageInspector
from fps_platform.shared.domain.clock import FakeClock
from tests.security.media.fixtures import MOMENT, corpus

EXPECTED_CODES = {
    "avif": MediaErrorCode.UNSUPPORTED_MEDIA_TYPE,
    "avif_truncated": MediaErrorCode.UNSUPPORTED_MEDIA_TYPE,
    "fake_mime_html": MediaErrorCode.UNSUPPORTED_MEDIA_TYPE,
    "fake_mime_png": MediaErrorCode.UNSUPPORTED_MEDIA_TYPE,
    "svg": MediaErrorCode.UNSUPPORTED_MEDIA_TYPE,
    "html": MediaErrorCode.UNSUPPORTED_MEDIA_TYPE,
    "exif_gps": MediaErrorCode.UNSUPPORTED_MEDIA_TYPE,
    "pixel_bomb": MediaErrorCode.MEDIA_TOO_LARGE,
    "empty": MediaErrorCode.MEDIA_CORRUPT,
    "truncated_jpeg": MediaErrorCode.MEDIA_CORRUPT,
    "corrupted_png": MediaErrorCode.MEDIA_CORRUPT,
}
MEDIA_ROOT = Path(__file__).resolve().parents[3] / "src" / "fps_platform" / "modules" / "media"


@pytest.mark.parametrize("name", ["jpeg", "png", "webp"])
def test_supported_images_produce_complete_evidence(name: str) -> None:
    fixture = next(item for item in corpus() if item.name == name)
    inspector = PillowImageInspector(FakeClock(MOMENT))

    evidence = inspector.inspect(fixture.body, content_type=fixture.declared_type)

    assert evidence.detected_mime.value == f"image/{name}"
    assert evidence.byte_size.value == len(fixture.body)
    assert evidence.dimensions.width > 0 and evidence.dimensions.height > 0
    assert len(evidence.checksum.digest) == 64
    assert evidence.inspected_at == MOMENT


@pytest.mark.parametrize("name", sorted(EXPECTED_CODES))
def test_hostile_images_are_rejected_before_evidence(name: str) -> None:
    fixture = next(item for item in corpus() if item.name == name)
    inspector = PillowImageInspector(FakeClock(MOMENT))

    with pytest.raises(MediaInspectionError) as raised:
        inspector.inspect(fixture.body, content_type=fixture.declared_type)

    assert raised.value.code == str(EXPECTED_CODES[name])


def test_byte_budget_is_enforced() -> None:
    fixture = next(item for item in corpus() if item.name == "jpeg")
    inspector = PillowImageInspector(FakeClock(MOMENT), policy=ImageInspectionPolicy(max_bytes=16))

    with pytest.raises(MediaInspectionError) as raised:
        inspector.inspect(fixture.body, content_type=fixture.declared_type)

    assert raised.value.code == str(MediaErrorCode.MEDIA_TOO_LARGE)


def test_pillow_is_imported_only_in_media_infrastructure() -> None:
    sources = sorted(MEDIA_ROOT.rglob("*.py"))
    importers = [
        path.name
        for path in sources
        if "from PIL" in path.read_text(encoding="utf-8")
        or "import PIL" in path.read_text(encoding="utf-8")
    ]

    assert importers == ["image_inspection.py"]

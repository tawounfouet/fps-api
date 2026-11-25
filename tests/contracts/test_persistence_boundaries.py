from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOMAIN_PATHS = (
    ROOT / "src/fps_platform/shared/domain",
    ROOT / "src/fps_platform/modules/audit/domain",
    ROOT / "src/fps_platform/modules/outbox/domain",
)
REPOSITORY_PATHS = (
    ROOT / "src/fps_platform/modules/audit/infrastructure/persistence/repository.py",
    ROOT / "src/fps_platform/modules/outbox/infrastructure/persistence/repository.py",
    ROOT / "tests/fixtures/persistence_probe.py",
)


def test_domain_has_no_sqlalchemy_import() -> None:
    for directory in DOMAIN_PATHS:
        for path in directory.rglob("*.py"):
            content = path.read_text(encoding="utf-8")
            assert "sqlalchemy" not in content.lower(), str(path)


def test_repositories_do_not_commit() -> None:
    for path in REPOSITORY_PATHS:
        content = path.read_text(encoding="utf-8")
        assert ".commit(" not in content, str(path)

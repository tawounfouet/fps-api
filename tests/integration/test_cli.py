from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


def run_script(
    name: str, environment: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, f"scripts/{name}"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_seed_is_idempotent() -> None:
    first = run_script("seed.py")
    second = run_script("seed.py")
    assert first.returncode == 0
    assert second.returncode == 0
    assert json.loads(first.stdout) == json.loads(second.stdout)
    payload = json.loads(first.stdout)
    assert payload["inserted"] == 0
    assert payload["seedable_foundation_configurations"] == 0


def test_diagnostics_are_safe(database_url: str) -> None:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url.replace("://fps@", "://fps:fps@")
    result = run_script("db_diagnostics.py", environment)
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["migration"] == "af1fb0f824bc"
    assert "url" not in payload
    assert "password" not in result.stdout.lower()

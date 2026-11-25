from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from uuid import uuid4

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.integration


def run_script(
    name: str,
    environment: dict[str, str] | None = None,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, f"scripts/{name}", *args],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def database_environment(database_url: str) -> dict[str, str]:
    environment = os.environ.copy()
    environment["DATABASE_URL"] = database_url.replace("://fps@", "://fps:fps@")
    return environment


def test_seed_is_idempotent(database_url: str) -> None:
    environment = database_environment(database_url)
    first = run_script("seed.py", environment)
    second = run_script("seed.py", environment)
    third = run_script("seed.py", environment)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    assert third.returncode == 0, third.stderr
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    third_payload = json.loads(third.stdout)
    assert first_payload["inserted"] == 4
    assert second_payload["inserted"] == 0
    assert second_payload == third_payload
    assert second_payload["seedable_foundation_configurations"] == 4
    assert second_payload["duplicates_skipped"] == 4


def test_bootstrap_super_admin_is_idempotent(database_url: str) -> None:
    environment = database_environment(database_url)
    subject = str(uuid4())
    args = (
        "--issuer",
        "https://idp.example.test",
        "--subject",
        subject,
        "--email",
        "admin@example.test",
        "--display-name",
        "Initial Admin",
    )
    first = run_script("bootstrap_super_admin.py", environment, *args)
    second = run_script("bootstrap_super_admin.py", environment, *args)
    assert first.returncode == 0, first.stderr
    assert second.returncode == 0, second.stderr
    first_payload = json.loads(first.stdout)
    second_payload = json.loads(second.stdout)
    assert first_payload["status"] == "ok"
    assert first_payload["created"] is True
    assert first_payload["changed"] is True
    assert second_payload["created"] is False
    assert second_payload["changed"] is False
    assert "email" not in first.stdout.lower()
    assert "subject" not in first.stdout.lower()


def test_bootstrap_refuses_second_super_admin(database_url: str) -> None:
    environment = database_environment(database_url)
    first = run_script(
        "bootstrap_super_admin.py",
        environment,
        "--issuer",
        "https://idp.example.test",
        "--subject",
        str(uuid4()),
        "--email",
        "first@example.test",
        "--display-name",
        "First Admin",
    )
    second = run_script(
        "bootstrap_super_admin.py",
        environment,
        "--issuer",
        "https://idp.example.test",
        "--subject",
        str(uuid4()),
        "--email",
        "second@example.test",
        "--display-name",
        "Second Admin",
    )
    assert first.returncode == 0, first.stderr
    assert second.returncode == 3, second.stderr
    assert json.loads(second.stdout)["code"] == "SUPER_ADMIN_EXISTS"


def test_diagnostics_are_safe(database_url: str) -> None:
    result = run_script("db_diagnostics.py", database_environment(database_url))
    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["status"] == "ok"
    assert payload["migration"] == "c8cfc1256c53"
    assert "url" not in payload
    assert "password" not in result.stdout.lower()

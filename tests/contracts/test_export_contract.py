from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient


def test_exported_openapi_is_deterministic() -> None:
    root = Path(__file__).resolve().parents[2]
    output = root / "openapi" / "openapi.json"
    before = output.read_text(encoding="utf-8")
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "export_openapi.py")],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    )
    after = output.read_text(encoding="utf-8")
    assert result.returncode == 0
    assert before == after
    schema = json.loads(after)
    assert schema["openapi"].startswith("3.1")
    assert "/health/live" in schema["paths"]
    assert "/health/ready" in schema["paths"]
    assert "/version" in schema["paths"]
    assert not any(path.startswith("/_test") for path in schema["paths"])
    assert "ErrorResponse" in schema["components"]["schemas"]


def test_openapi_response_model_requires_contract_keys(client: TestClient) -> None:
    app = cast(FastAPI, client.app)
    schema = app.openapi()
    error_schema = schema["components"]["schemas"]["ErrorResponse"]
    assert set(error_schema["required"]) == {"code", "message", "details", "correlation_id"}

from __future__ import annotations

import os

import pytest

from .test_minio_contract import endpoint_is_reachable, run_storage_contract

REQUIRED_VARIABLES = (
    "FPS_R2_SANDBOX_ENDPOINT_URL",
    "FPS_R2_SANDBOX_ACCESS_KEY_ID",
    "FPS_R2_SANDBOX_SECRET_ACCESS_KEY",
    "FPS_R2_SANDBOX_BUCKET",
)


def test_r2_sandbox_contract() -> None:
    if os.environ.get("FPS_R2_SANDBOX_GO") != "1" or any(
        not os.environ.get(name) for name in REQUIRED_VARIABLES
    ):
        pytest.skip("NOT_EXECUTED: R2 sandbox opt-in and explicit variables are required")
    endpoint_url = os.environ["FPS_R2_SANDBOX_ENDPOINT_URL"]
    if not endpoint_is_reachable(endpoint_url):
        pytest.skip("NOT_EXECUTED: R2 sandbox endpoint is not reachable")
    run_storage_contract(
        endpoint_url=endpoint_url,
        bucket=os.environ["FPS_R2_SANDBOX_BUCKET"],
        region=os.environ.get("FPS_R2_SANDBOX_REGION", "auto"),
        access_key_id=os.environ["FPS_R2_SANDBOX_ACCESS_KEY_ID"],
        secret_access_key=os.environ["FPS_R2_SANDBOX_SECRET_ACCESS_KEY"],
    )

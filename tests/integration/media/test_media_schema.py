from __future__ import annotations

import pytest
from sqlalchemy import inspect
from sqlalchemy.engine import Engine

pytestmark = pytest.mark.integration


def test_media_assets_has_intent_claim_and_proof_columns(engine: Engine) -> None:
    columns = {item["name"] for item in inspect(engine).get_columns("media_assets")}
    assert {
        "intent_expires_at",
        "claimed_at",
        "claim_owner",
        "attempt_count",
        "failure_code",
        "detected_mime",
        "promotion_proof_id",
        "promoted_at",
        "verified_at",
    } <= columns

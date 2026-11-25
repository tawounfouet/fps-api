from __future__ import annotations

import json
import time
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

from fps_platform.modules.identity.domain.exceptions import TokenValidationError
from fps_platform.modules.identity.infrastructure.oidc.jwks import JwksCache
from fps_platform.modules.identity.infrastructure.oidc.validator import JwksTokenValidator

ISSUER = "https://idp.example.test"
AUDIENCE = "fps-api"


class FakeFetcher:
    def __init__(self, *payloads: dict[str, Any]) -> None:
        self.payloads = list(payloads)
        self.calls = 0

    def fetch(self) -> dict[str, Any]:
        index = min(self.calls, len(self.payloads) - 1)
        self.calls += 1
        return self.payloads[index]


def make_key(kid: str = "key-1") -> tuple[Any, Any, dict[str, Any]]:
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()
    key = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(public_key))
    key.update({"kid": kid, "use": "sig", "alg": "RS256"})
    return private_key, public_key, key


def make_token(private_key: Any, *, subject: str = "user-1", kid: str = "key-1") -> str:
    now = int(time.time())
    return jwt.encode(
        {
            "sub": subject,
            "iss": ISSUER,
            "aud": AUDIENCE,
            "iat": now,
            "nbf": now - 5,
            "exp": now + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": kid},
    )


def make_validator(fetcher: FakeFetcher) -> JwksTokenValidator:
    return JwksTokenValidator(
        issuer=ISSUER,
        audience=AUDIENCE,
        algorithms=["RS256"],
        jwks=JwksCache(fetcher, ttl_seconds=300),
        leeway_seconds=30,
    )


def test_valid_token_is_accepted() -> None:
    private_key, _, key = make_key()
    validator = make_validator(FakeFetcher({"keys": [key]}))
    identity = validator.validate(make_token(private_key))
    assert identity.issuer == ISSUER
    assert identity.subject == "user-1"


def test_bad_audience_is_rejected() -> None:
    private_key, _, key = make_key()
    validator = make_validator(FakeFetcher({"keys": [key]}))
    token = jwt.encode(
        {
            "sub": "user-1",
            "iss": ISSUER,
            "aud": "other-api",
            "exp": int(time.time()) + 300,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "key-1"},
    )
    with pytest.raises(TokenValidationError):
        validator.validate(token)


def test_expired_token_is_rejected() -> None:
    private_key, _, key = make_key()
    validator = make_validator(FakeFetcher({"keys": [key]}))
    token = jwt.encode(
        {
            "sub": "user-1",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": int(time.time()) - 120,
        },
        private_key,
        algorithm="RS256",
        headers={"kid": "key-1"},
    )
    with pytest.raises(TokenValidationError):
        validator.validate(token)


def test_disallowed_algorithm_is_rejected() -> None:
    _, _, key = make_key()
    validator = make_validator(FakeFetcher({"keys": [key]}))
    token = jwt.encode(
        {
            "sub": "user-1",
            "iss": ISSUER,
            "aud": AUDIENCE,
            "exp": int(time.time()) + 300,
        },
        "shared-secret-with-at-least-thirty-two-bytes",
        algorithm="HS256",
        headers={"kid": "key-1"},
    )
    with pytest.raises(TokenValidationError):
        validator.validate(token)


def test_rotated_key_is_refreshed() -> None:
    old_private_key, _, old_key = make_key("old")
    new_private_key, _, new_key = make_key("new")
    fetcher = FakeFetcher({"keys": [old_key]}, {"keys": [new_key]})
    validator = make_validator(fetcher)
    identity = validator.validate(make_token(new_private_key, kid="new"))
    assert identity.subject == "user-1"
    assert fetcher.calls == 2
    assert old_private_key is not None


def test_jwks_cache_reuses_keys_until_expiry() -> None:
    _, _, key = make_key()
    clock_values = [0.0, 10.0, 400.0]
    index = 0

    def monotonic() -> float:
        nonlocal index
        value = clock_values[min(index, len(clock_values) - 1)]
        index += 1
        return value

    fetcher = FakeFetcher({"keys": [key]})
    cache = JwksCache(fetcher, ttl_seconds=300, monotonic=monotonic)
    assert len(cache.keys()) == 1
    assert len(cache.keys()) == 1
    assert len(cache.keys()) == 1
    assert fetcher.calls == 2

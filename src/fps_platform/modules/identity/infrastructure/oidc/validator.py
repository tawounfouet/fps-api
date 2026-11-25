from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import jwt
from jwt.exceptions import PyJWTError

from fps_platform.modules.identity.domain.exceptions import TokenValidationError
from fps_platform.modules.identity.domain.ports import VerifiedIdentity, VerifiedIdentityProvider
from fps_platform.modules.identity.infrastructure.oidc.jwks import JwksCache

ALLOWED_KEY_TYPES: dict[str, str] = {
    "RS256": "RSA",
    "PS256": "RSA",
    "ES256": "EC",
}


class JwksTokenValidator(VerifiedIdentityProvider):
    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        algorithms: Sequence[str],
        jwks: JwksCache,
        leeway_seconds: int,
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.algorithms = tuple(algorithms)
        self.jwks = jwks
        self.leeway_seconds = leeway_seconds

    def validate(self, token: str) -> VerifiedIdentity:
        if not token or len(token) > 8192:
            raise TokenValidationError("token is invalid")
        header = self._header(token)
        algorithm = str(header.get("alg", ""))
        if algorithm not in self.algorithms:
            raise TokenValidationError("token algorithm is not allowed")
        if "jku" in header or "x5u" in header:
            raise TokenValidationError("token key URL is not allowed")
        key_id = header.get("kid")
        if key_id is not None and (not isinstance(key_id, str) or len(key_id) > 256):
            raise TokenValidationError("token key id is invalid")

        identity = self._try_keys(self.jwks.keys(), token, algorithm, key_id)
        if identity is not None:
            return identity
        identity = self._try_keys(self.jwks.keys(refresh=True), token, algorithm, key_id)
        if identity is not None:
            return identity
        raise TokenValidationError("token could not be validated")

    def _header(self, token: str) -> dict[str, Any]:
        try:
            header = jwt.get_unverified_header(token)
        except PyJWTError as exc:
            raise TokenValidationError("token header is invalid") from exc
        if not isinstance(header, dict):
            raise TokenValidationError("token header is invalid")
        return header

    def _try_keys(
        self,
        keys: Sequence[dict[str, Any]],
        token: str,
        algorithm: str,
        key_id: str | None,
    ) -> VerifiedIdentity | None:
        for key in keys:
            if key_id is not None and key.get("kid") != key_id:
                continue
            if key.get("alg") is not None and key.get("alg") != algorithm:
                continue
            if key.get("kty") != ALLOWED_KEY_TYPES.get(algorithm):
                continue
            try:
                public_key = jwt.PyJWK.from_dict(key, algorithm=algorithm).key
                claims = jwt.decode(
                    token,
                    key=public_key,
                    algorithms=[algorithm],
                    audience=self.audience,
                    issuer=self.issuer,
                    leeway=self.leeway_seconds,
                    options={
                        "require": ["exp", "iss", "aud", "sub"],
                        "verify_nbf": True,
                    },
                )
            except PyJWTError:
                continue
            subject = claims.get("sub")
            if not isinstance(subject, str) or not subject:
                raise TokenValidationError("token subject is invalid")
            return VerifiedIdentity(issuer=self.issuer, subject=subject)
        return None

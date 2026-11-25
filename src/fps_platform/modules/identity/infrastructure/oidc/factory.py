from __future__ import annotations

from fps_platform.config import Settings
from fps_platform.modules.identity.domain.ports import VerifiedIdentityProvider
from fps_platform.modules.identity.infrastructure.oidc.jwks import HttpJwksFetcher, JwksCache
from fps_platform.modules.identity.infrastructure.oidc.validator import JwksTokenValidator


def build_token_validator(settings: Settings) -> VerifiedIdentityProvider | None:
    if not settings.oidc_enabled:
        return None
    if (
        settings.oidc_issuer is None
        or settings.oidc_audience is None
        or settings.oidc_jwks_url is None
    ):
        return None
    jwks = JwksCache(
        HttpJwksFetcher(settings.oidc_jwks_url),
        ttl_seconds=settings.oidc_jwks_cache_ttl_seconds,
    )
    return JwksTokenValidator(
        issuer=settings.oidc_issuer,
        audience=settings.oidc_audience,
        algorithms=settings.oidc_algorithms,
        jwks=jwks,
        leeway_seconds=settings.oidc_clock_leeway_seconds,
    )

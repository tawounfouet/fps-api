from __future__ import annotations

import os
import sys
from argparse import ArgumentParser
from collections.abc import Mapping, Sequence

PRODUCTION_VALUE = "production"
PRODUCTION_KEYS = ("ENVIRONMENT", "DJANGO_ENV")
ALLOWED_MODES = ("fake", "s3")


def is_production(environ: Mapping[str, str]) -> bool:
    return any(environ.get(key, "").strip().lower() == PRODUCTION_VALUE for key in PRODUCTION_KEYS)


def check_mode(environ: Mapping[str, str]) -> tuple[int, str]:
    mode = environ.get("MEDIA_STORAGE_MODE", ALLOWED_MODES[0]).strip().lower()
    if mode not in ALLOWED_MODES:
        return 1, "media_storage_mode_invalid: expected fake or s3"
    if mode == "fake" and is_production(environ):
        return 1, "media_storage_mode_refused: fake is not allowed in production"
    return 0, f"media_storage_mode_ok: mode={mode} production={str(is_production(environ)).lower()}"


def main(argv: Sequence[str] | None = None) -> int:
    parser = ArgumentParser(description="Guard MEDIA_STORAGE_MODE before deployment")
    parser.parse_args(argv)
    code, message = check_mode(os.environ)
    print(message)
    return code


if __name__ == "__main__":
    sys.exit(main())

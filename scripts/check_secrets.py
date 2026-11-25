from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

PATTERNS = {
    "private_key": re.compile(r"-----BEGIN (?:RSA|OPENSSH|EC|DSA|PRIVATE) PRIVATE KEY-----"),
    "aws_access_key": re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    "openai_key": re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"),
    "github_token": re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    "slack_token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}\b"),
    "postgres_password_assignment": re.compile("POSTGRES_" + "PASSWORD:" + r"\s*\S+"),
}

SKIPPED_PATHS: set[str] = set()
SKIPPED_PREFIXES = ("docs/qualification/",)


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    tracked = subprocess.check_output(
        ["git", "ls-files"], cwd=root, text=True, encoding="utf-8"
    ).splitlines()
    findings: list[str] = []
    for relative_path in tracked:
        if relative_path in SKIPPED_PATHS or relative_path.startswith(SKIPPED_PREFIXES):
            continue
        path = root / relative_path
        if not path.is_file():
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name, pattern in PATTERNS.items():
            if pattern.search(content):
                findings.append(f"{relative_path}: {name}")
    if findings:
        print("secret_scan_failed")
        for finding in findings:
            print(finding)
        return 1
    print(f"secret_scan_ok files={len(tracked)} patterns={len(PATTERNS)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

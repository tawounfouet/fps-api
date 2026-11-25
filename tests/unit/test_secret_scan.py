from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_secret_scan_passes_on_tracked_files() -> None:
    root = Path(__file__).resolve().parents[2]
    script = root / "scripts" / "check_secrets.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert "secret_scan_ok" in result.stdout

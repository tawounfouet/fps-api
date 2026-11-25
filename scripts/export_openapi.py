from __future__ import annotations

import json
from pathlib import Path

from fps_platform.bootstrap import create_app
from fps_platform.config import Environment, Settings


def main() -> None:
    settings = Settings(
        _env_file=None,
        environment=Environment.TEST,
        docs_enabled=True,
        allowed_origins=["http://localhost:3000"],
        database_url=None,
    )
    app = create_app(settings)
    schema = app.openapi()
    root = Path(__file__).resolve().parents[1]
    output = root / "openapi" / "openapi.json"
    output.write_text(
        json.dumps(schema, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {output.relative_to(root)}")


if __name__ == "__main__":
    main()

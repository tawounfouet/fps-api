from __future__ import annotations

import json
import sys


def main() -> int:
    print(
        json.dumps(
            {
                "status": "ok",
                "seedable_foundation_configurations": 0,
                "inserted": 0,
                "duplicates_skipped": 0,
                "reason": "no M2 foundation configuration table",
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())

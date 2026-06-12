#!/usr/bin/env python3
"""Generate the daily Codex report and prompt for the next continuation."""
from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.codex_daily_automation_engine import write_daily_outputs


def main() -> int:
    result = write_daily_outputs(ROOT)
    report = result["report"]
    print(json.dumps({
        "ok": True,
        "version": report["version"],
        "markdown": result["markdown"],
        "json": result["json"],
        "prompt": result["prompt"],
        "cleanliness": report["cleanliness"],
        "zip": report["zip"],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""V745 alerts foundation check."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.alerts_engine import alerts_foundation_snapshot


def main() -> int:
    snapshot = alerts_foundation_snapshot(enabled=False)
    result = {"ok": bool(snapshot.get("ok") and snapshot.get("enabled") is False), "types": len(snapshot.get("types") or [])}
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

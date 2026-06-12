#!/usr/bin/env python3
"""Validate V743 data ownership classification."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from engines.data_vault_engine import CRITICAL_TABLES, OWNERSHIP


def main() -> int:
    missing = [table for table in CRITICAL_TABLES if table not in OWNERSHIP]
    result = {
        "ok": not missing,
        "classified": len(CRITICAL_TABLES) - len(missing),
        "total": len(CRITICAL_TABLES),
        "missing": missing,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

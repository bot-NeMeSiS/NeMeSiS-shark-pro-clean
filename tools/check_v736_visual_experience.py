#!/usr/bin/env python3
"""Validate V736 global client visual membership experience without running Flask."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.visual_experience_engine import visual_experience_snapshot  # noqa: E402


def main() -> int:
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    snapshot = visual_experience_snapshot(version)
    report = {
        "ok": snapshot["score"] >= 95,
        "version": version,
        "score": snapshot["score"],
        "status": snapshot["status"],
        "covered_templates": snapshot["covered_templates"],
        "total_templates": snapshot["total_templates"],
        "risks": snapshot["risks"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Validate V738 final commercial release candidate layer without running Flask."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.final_release_engine import final_release_snapshot  # noqa: E402


def main() -> int:
    version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
    os.environ.setdefault("DB_PATH", "/tmp/nemesis_v738_check.db")
    snapshot = final_release_snapshot(os.environ.get("DB_PATH", "/tmp/nemesis_v738_check.db"), app_version=version)
    static_gates = {gate["key"]: gate["score"] for gate in snapshot["gates"][:3]}
    report = {
        "ok": snapshot["project"]["version_match"] and all(score >= 90 for score in static_gates.values()),
        "version": version,
        "status": snapshot["status"],
        "readiness_score": snapshot["readiness_score"],
        "static_gates": static_gates,
        "production_missing": snapshot["production_missing"],
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

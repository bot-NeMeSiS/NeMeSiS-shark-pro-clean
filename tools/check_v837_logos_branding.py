#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = (ROOT / "templates" / "base.html").read_text(encoding="utf-8", errors="replace")
CSS = (ROOT / "static" / "app.css").read_text(encoding="utf-8", errors="replace")


def main() -> int:
    checks = {
        "shark_logo_exists": (ROOT / "static" / "img" / "shark-logo.svg").exists(),
        "favicon_svg": 'rel="icon"' in BASE and "shark-logo.svg" in BASE,
        "brand_visible": "NeMeSiS" in BASE and "SHARK PRO" in BASE,
        "logo_fit": "object-fit:contain" in CSS,
        "logo_glow": "drop-shadow" in CSS,
        "v837_css": "V837 REFERENCE PHOTO PERFECTION REAL QA START" in CSS,
    }
    missing = [k for k, v in checks.items() if not v]
    print(json.dumps({"ok": not missing, "missing": missing}, ensure_ascii=False, indent=2))
    return 0 if not missing else 1


if __name__ == "__main__":
    raise SystemExit(main())

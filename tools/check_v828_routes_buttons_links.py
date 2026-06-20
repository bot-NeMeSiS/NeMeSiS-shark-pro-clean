#!/usr/bin/env python3
from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "templates"
REPORT = ROOT / "reports" / "V828_ROUTES_BUTTONS_LINKS_AUDIT.md"


def main() -> int:
    hrefs = []
    missing_href = []
    for path in TEMPLATES.glob("*.html"):
        text = path.read_text(encoding="utf-8", errors="replace")
        hrefs.extend(re.findall(r'href=["\']([^"\']+)["\']', text))
        for match in re.finditer(r"<a\b(?![^>]*\bhref=)[^>]*>", text, flags=re.I):
            missing_href.append(f"{path.name}:{text[:match.start()].count(chr(10)) + 1}")
    broken_literal = [href for href in hrefs if "{{ title or" in href or "Lorem" in href]
    text = REPORT.read_text(encoding="utf-8") if REPORT.exists() else ""
    ok = REPORT.exists() and not broken_literal and len(missing_href) <= 30 and "V828" in text
    print(json.dumps({
        "ok": ok,
        "hrefs_found": len(hrefs),
        "anchor_without_href_review": missing_href[:20],
        "broken_literal": broken_literal[:20],
        "report_exists": REPORT.exists(),
    }, ensure_ascii=False, indent=2))
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())



#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
css = (ROOT / 'static' / 'app.css').read_text(encoding='utf-8', errors='replace')

def main() -> int:
    checks = {
        'mobile_media_980': '@media(max-width:980px)' in css and 'data-v826-shell="true"' in css,
        'mobile_media_560': '@media(max-width:560px)' in css and 'data-v826-shell="true"' in css,
        'bottom_nav_mobile_unique_style': 'grid-template-columns:repeat(5,minmax(0,1fr))' in css,
        'shark_safe_bottom': 'env(safe-area-inset-bottom' in css and '.shark-widget' in css,
        'no_horizontal_overflow_intent': 'width:calc(100% - 14px)' in css or 'width:min(100% - 24px' in css,
        'mobile_shark_background_softened': 'opacity:.065' in css and 'shark-dot-watermark' in css,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == '__main__':
    raise SystemExit(main())



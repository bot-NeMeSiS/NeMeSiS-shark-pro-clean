#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
css=(ROOT/'static/app.css').read_text(encoding='utf-8', errors='replace')
def main() -> int:
    checks={
        'mobile_980_rules': '@media(max-width:980px)' in css and 'data-v827-shell="true"' in css,
        'mobile_560_rules': '@media(max-width:560px)' in css and 'data-v827-shell="true"' in css,
        'single_mobile_bottom_nav_style': 'grid-template-columns:repeat(5,minmax(0,1fr))' in css,
        'safe_area_bottom': 'env(safe-area-inset-bottom' in css,
        'mobile_shark_soft': 'opacity:.075' in css and 'shark-dot-watermark' in css,
        'mobile_panel_above_nav': 'bottom:calc(140px + env(safe-area-inset-bottom,0px))' in css,
        'no_horizontal_width_intent': 'width:calc(100% - 14px)' in css or 'width:min(100% - 28px' in css,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'ok': not failed, 'failed': failed, 'checks': checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0
if __name__ == '__main__':
    raise SystemExit(main())

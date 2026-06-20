#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
base=(ROOT/'templates/base.html').read_text(encoding='utf-8', errors='replace')
css=(ROOT/'static/app.css').read_text(encoding='utf-8', errors='replace')
def main() -> int:
    checks={
        'component_macros_exist': (ROOT/'templates/components/v827_design_system.html').exists(),
        'design_tokens': all(x in css for x in ['--v827-bg','--v827-surface','--v827-cyan','--v827-radius-xl']),
        'single_topbar': base.count('class="top ns-topbar"') == 1,
        'single_bottom_nav': base.count('class="bottom-nav bottom-nav-clean"') == 1,
        'single_shark_widget': base.count('id="sharkWidget"') == 1 and base.count('id="sharkFab"') == 1,
        'client_background': 'v825-shark-background' in base and 'shark-dot-watermark' in css,
        'v827_hero_system': all(x in css for x in ['.v799-appbar', '.v812-hero-shell', '.v774-client-hero']),
        'v827_cards_system': all(x in css for x in ['.v799-agenda-row', '.v799-live-card', '.v799-pick-card']),
        'v827_buttons_system': '.v827-btn' in css and '.btn.primary' in css,
        'admin_separated': '.ns-admin .v825-shark-background' in css and '.ns-admin .shark-widget' in css,
        'shark_no_duplicate_on_shark': '[data-ns-route="/shark"] .shark-widget' in css and '[data-ns-route="/shark"] .v825-public-floating-shark' in css,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'ok': not failed, 'failed': failed, 'checks': checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0
if __name__ == '__main__':
    raise SystemExit(main())



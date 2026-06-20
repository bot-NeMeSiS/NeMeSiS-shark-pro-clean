#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSION = "V827_REFERENCE_PHOTO_REBUILD_DESIGN_SYSTEM_FINAL"
CURRENT = "V829_MOBILE_LINKED_ECOSYSTEM_FINAL_APP_EXPERIENCE"
def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="replace")
def main() -> int:
    app, base, css = read('app.py'), read('templates/base.html'), read('static/app.css')
    checks = {
        'version_txt_current_or_v827': (ROOT/'VERSION.txt').read_text(encoding='utf-8-sig').strip() in {VERSION, CURRENT},
        'app_version_current_or_v827': any(token in app for token in [f"APP_VERSION = '{VERSION}'", f'APP_VERSION = "{VERSION}"', f"APP_VERSION = '{CURRENT}'", f'APP_VERSION = "{CURRENT}"']),
        'base_meta_current_or_v827': f'name="nemesis-version" content="{VERSION}"' in base or f'name="nemesis-version" content="{CURRENT}"' in base,
        'base_cache_current_or_v827': f'?v={VERSION}' in base or f'?v={CURRENT}' in base,
        'base_shell_v827': 'data-v827-shell="true"' in base,
        'base_comment_v827': 'NEMESIS V827 REFERENCE PHOTO REBUILD DESIGN SYSTEM ACTIVE' in base,
        'css_marker_v827': 'V827 REFERENCE PHOTO REBUILD DESIGN SYSTEM START' in css and 'V827 REFERENCE PHOTO REBUILD DESIGN SYSTEM END' in css,
        'runtime_keys_v827': all(k in app for k in ['has_v827_shell','has_v827_css','has_v826_full_screen','has_v825_shark_identity','has_v818_automation']),
        'v826_preserved': 'data-v826-shell="true"' in base and 'V826 FULL REFERENCE EXPERIENCE START' in css,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'ok': not failed, 'failed': failed, 'checks': checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0
if __name__ == '__main__':
    raise SystemExit(main())



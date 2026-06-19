#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = (ROOT / 'app.py').read_text(encoding='utf-8', errors='replace')
base = (ROOT / 'templates' / 'base.html').read_text(encoding='utf-8', errors='replace')
css = (ROOT / 'static' / 'app.css').read_text(encoding='utf-8', errors='replace')

def main() -> int:
    checks = {
        'v818_master_tick_preserved': '/api/automation/master-tick' in app and 'daily_automation_engine' in app,
        'v819_dedup_preserved': 'data-v819-shell="true"' in base and 'V819 REFERENCE UI DEDUP LAYER PURGE START' in css,
        'v820_crests_preserved': 'data-v820-shell="true"' in base and 'V820 REAL CRESTS REFERENCE VISUAL PIXEL POLISH START' in css,
        'v821_hotfix_preserved': 'data-v821-shell="true"' in base and 'last_502_hotfix' in app,
        'v822_stability_preserved': 'data-v822-shell="true"' in base and 'v822_runtime_stability_snapshot' in app,
        'v823_visual_preserved': 'data-v823-shell="true"' in base and 'V823 RENDER VIDEO REFERENCE REAL CRESTS PIXEL EXPERIENCE START' in css,
        'v824_visual_preserved': 'data-v824-shell="true"' in base and 'V824 RENDER VIDEO PIXEL MATCH FINAL APP EXPERIENCE START' in css,
        'v825_identity_preserved': 'data-v825-shell="true"' in base and 'V825 SHARK IDENTITY FLOATING BACKGROUND REFERENCE START' in css,
        'v826_active': 'data-v826-shell="true"' in base and 'V826 FULL REFERENCE EXPERIENCE START' in css,
        'db_path_unchanged': "DB_PATH" in app and "/data/database.db" in app,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == '__main__':
    raise SystemExit(main())

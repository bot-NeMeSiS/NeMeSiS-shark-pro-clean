#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CURRENT="V832_FULL_APP_REFERENCE_VISUAL_GITHUB_RENDER_WORKFLOW_FINAL"
def read(rel): return (ROOT/rel).read_text(encoding='utf-8', errors='replace')
def main():
    app=read('app.py'); base=read('templates/base.html'); css=read('static/app.css'); version=read('VERSION.txt').strip().lstrip('ï»¿')
    checks={
      'version_current': version == CURRENT,
      'app_version_current': f"APP_VERSION = '{CURRENT}'" in app or f'APP_VERSION = "{CURRENT}"' in app,
      'base_meta_current': f'name="nemesis-version" content="{CURRENT}"' in base,
      'base_cache_current': f'?v={CURRENT}' in base,
      'base_shell_v821': 'data-v821-shell="true"' in base,
      'runtime_v818_to_v827_keys': all(k in app for k in ['has_v827_shell','has_v826_full_screen','has_v825_shark_identity','has_v824_visual','has_v823_visual','has_v822_stability','has_v821_hotfix','has_v820_crests','has_v819_dedup','has_v818_automation']),
      'v818_master_tick': '/api/automation/master-tick' in app,
      'v820_crest_routes': all(x in app for x in ['/asset/team-logo/', '/asset/league-logo/', '/team-crest.svg']),
      'v827_css_active': 'V827 REFERENCE PHOTO REBUILD DESIGN SYSTEM START' in css,
    }
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({'ok': not failed, 'failed': failed, 'checks': checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0
if __name__=='__main__': raise SystemExit(main())



#!/usr/bin/env python3
from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
CURRENT="V828_REFERENCE_PIXEL_PARITY_FULL_ECOSYSTEM_FINAL"
def read(rel): return (ROOT/rel).read_text(encoding='utf-8', errors='replace')
def main():
    app=read('app.py'); base=read('templates/base.html'); css=read('static/app.css'); version=read('VERSION.txt').strip().lstrip('ï»¿')
    checks={
      'version_current_or_v818': version in {'V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL', CURRENT},
      'app_version_current_or_v818': 'APP_VERSION' in app and (CURRENT in app or 'V818_DAILY_AUTOMATION_OPERATING_SYSTEM_FINAL' in app),
      'master_tick_route': '/api/automation/master-tick' in app,
      'health_check_route': '/api/automation/health-check' in app,
      'daily_engine_present': 'daily_automation_engine' in app,
      'base_v818_shell': 'data-v818-shell="true"' in base,
      'css_v818_marker': 'V818' in css,
    }
    missing=[k for k,v in checks.items() if not v]
    print({'ok': not missing, 'check':'v818_daily_automation_os', 'missing': missing, 'checks': checks})
    return 1 if missing else 0
if __name__=='__main__': raise SystemExit(main())


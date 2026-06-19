#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
required = {
    'home.html':'home','client_login.html':'client_login','register.html':'register','client_app_center.html':'client_app_center','calendar.html':'calendar','live.html':'live','picks.html':'picks','match_detail.html':'match_detail','shark.html':'shark','shark_core.html':'shark_core','profile.html':'profile','telegram.html':'telegram','support.html':'support','favorites.html':'favorites','track_record.html':'track_record','combis.html':'combis','betting_markets.html':'betting_markets','highlights.html':'highlights','admin_dashboard.html':'admin_dashboard','admin_navigation_map.html':'admin_navigation_map','admin_daily_automation.html':'admin_daily_automation','admin_telegram_command_center.html':'admin_telegram_command_center','admin_users.html':'admin_users','admin_memberships.html':'admin_memberships','admin_matches_sync.html':'admin_matches_sync','admin_data_center.html':'admin_data_center','admin_payments.html':'admin_payments','admin_final_certification.html':'admin_final_certification'
}

def main() -> int:
    checks = {}
    for filename, marker in required.items():
        p = ROOT / 'templates' / filename
        checks[f'{filename}_exists'] = p.exists()
        checks[f'{filename}_v826'] = p.exists() and f'data-v826-template="{marker}"' in p.read_text(encoding='utf-8', errors='replace')
    failed=[k for k,v in checks.items() if not v]
    print(json.dumps({"ok": not failed, "failed": failed, "covered_templates": len(required), "checks": checks}, ensure_ascii=False, indent=2))
    return 1 if failed else 0

if __name__ == '__main__':
    raise SystemExit(main())

#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSIONS = {"V806_CLIENT_REFERENCE_UI_NO_LEFT_RAIL_FLOW_PERFECTION", "V807_ADMIN_CLIENT_REFERENCE_NAVIGATION_COMMAND_CENTER_REAL_DATA_FINAL", "V808_FULL_ECOSYSTEM_REFERENCE_UI_ADMIN_CLIENT_FINAL_PERFECTION", "V809_REFERENCE_PHOTO_EXACT_UI_ADMIN_CLIENT_BUTTONS_FINAL", "V810_TELEGRAM_PRO_CHANNEL_REFERENCE_TOPBAR_SHARK_UI_FINAL_POLISH", "V811_CLIENT_MATCH_LIFECYCLE_LIVE_FIELD_REFERENCE_UI_FINAL"}
VERSION = "V806_CLIENT_REFERENCE_UI_NO_LEFT_RAIL_FLOW_PERFECTION"

checks = []

def ok(name, condition):
    checks.append((name, bool(condition)))

base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
app = (ROOT / "app.py").read_text(encoding="utf-8")

ok("version file", version in VERSIONS)
ok("app version", any(f"APP_VERSION = '{v}'" in app for v in VERSIONS))
ok("v806 shell attr", 'data-v806-shell="true"' in base)
ok("client rail block removed from base", '<aside class="v798-client-rail v799-client-rail"' not in base)
ok("rail css defensively hidden", '.v799-client-rail' in css and 'display:none!important' in css)
ok("main shell centered", 'margin-left:auto!important' in css and 'max-width:1280px!important' in css)
ok("mobile bottom nav account", '<a href="/mi-cuenta" data-v775-icon="◎">Cuenta</a>' in base)
ok("logout still in top nav", 'v797-nav-logout' in base and 'Salir' in base)
ok("no fake live data copy", 'no se inventa' in (ROOT / "reports" / "V806_CLIENT_REFERENCE_UI_NO_LEFT_RAIL_FLOW_PERFECTION_REPORT.md").read_text(encoding="utf-8"))

failed = [name for name, passed in checks if not passed]
for name, passed in checks:
    print(("OK" if passed else "FAIL"), name)
if failed:
    raise SystemExit("V806 check failed: " + ", ".join(failed))
print("V806 client reference UI no-left-rail check OK")

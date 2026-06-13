#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]

checks = []

def ok(name, cond):
    checks.append((name, bool(cond)))

app = (ROOT / "app.py").read_text(encoding="utf-8")
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
combis = (ROOT / "templates" / "combis.html").read_text(encoding="utf-8")
markets_tpl = (ROOT / "templates" / "betting_markets.html").read_text(encoding="utf-8")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()

ok("version_v765", version in {"V765_MARKETS_COMBIS_CLIENT_STRUCTURE_POLISH", "V766_CALENDAR_RESULTS_HIGHLIGHTS_ORDER_AUTOMATION", "V767_MADRID_TIME_EVERYWHERE_CERTIFICATION"})
ok("app_version_v765", 'APP_VERSION = "V765_MARKETS_COMBIS_CLIENT_STRUCTURE_POLISH"' in app or 'APP_VERSION = "V766_CALENDAR_RESULTS_HIGHLIGHTS_ORDER_AUTOMATION"' in app or 'APP_VERSION = "V767_MADRID_TIME_EVERYWHERE_CERTIFICATION"' in app)
ok("engine_exists", (ROOT / "engines" / "betting_markets_engine.py").exists())
ok("markets_route", '@app.route("/mercados")' in app and 'betting_markets_page' in app)
ok("markets_api", '/api/client/betting-markets' in app and 'api_client_betting_markets' in app)
ok("v765_contexts", 'v765_markets_context' in app and 'v765_combi_context' in app)
ok("nav_markets", '/mercados' in base)
ok("markets_template", 'Mercados básicos y combis responsables' in markets_tpl)
ok("combis_fixed_links", '/combispartidos=' not in combis and '/sharkcombi=' not in combis)
ok("combis_strategies", 'Combi 1X2' in combis and 'Combi de goles' in combis and 'Combi mixta' in combis)
ok("home_markets", 'v765-home-markets' in (ROOT / "templates" / "home.html").read_text(encoding="utf-8"))
ok("picks_market_control", 'v765-picks-market-control' in (ROOT / "templates" / "picks.html").read_text(encoding="utf-8"))
ok("calendar_order_strip", 'v765-screen-order-strip' in (ROOT / "templates" / "calendar.html").read_text(encoding="utf-8"))
ok("live_order_strip", 'v765-screen-order-strip' in (ROOT / "templates" / "live.html").read_text(encoding="utf-8"))
ok("match_markets", 'v765-match-markets' in (ROOT / "templates" / "match_detail.html").read_text(encoding="utf-8"))
ok("css_v765", 'V765_MARKETS_COMBIS_CLIENT_STRUCTURE_POLISH' in css)
ok("telegram_preserved", '/api/automation/telegram/tick' in app and (ROOT / "tools" / "render_cron_telegram_tick.py").exists())
ok("db_path_preserved", 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' in app)
ok("madrid_time_preserved", 'Europe/Madrid' in app)

# Detect broken hrefs such as /combispartidos=3 or /sharkpick=...
bad = []
for path in (ROOT / "templates").rglob("*.html"):
    text = path.read_text(encoding="utf-8", errors="ignore")
    for href in re.findall(r'href="(/[^"]*)"', text):
        if re.search(r'/(?:[a-zA-Z0-9_-]+)(?:lane=|f=|partidos=|pick=|match=|combi=)', href) and '?' not in href and '&' not in href:
            bad.append((str(path.relative_to(ROOT)), href))
ok("no_malformed_query_links", not bad)

failed = [name for name, value in checks if not value]
for name, value in checks:
    print(f"{'OK' if value else 'FAIL'} {name}")
if bad:
    print("Malformed links:", bad[:20])
if failed:
    raise SystemExit("V765 check failed: " + ", ".join(failed))
print("V765 markets/combis/client-structure check OK")

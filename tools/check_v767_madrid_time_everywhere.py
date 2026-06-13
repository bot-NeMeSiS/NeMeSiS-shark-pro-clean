#!/usr/bin/env python3
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V767_MADRID_TIME_EVERYWHERE_CERTIFICATION"

failures: list[str] = []

def ok(name: str, condition: bool, detail: str = "") -> None:
    if condition:
        print(f"[OK] {name}{(' - ' + detail) if detail else ''}")
    else:
        print(f"[FAIL] {name}{(' - ' + detail) if detail else ''}")
        failures.append(name)

version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
app = (ROOT / "app.py").read_text(encoding="utf-8")
engine = (ROOT / "engines" / "madrid_time_engine.py").read_text(encoding="utf-8")
spanish = (ROOT / "engines" / "spanish_localization_engine.py").read_text(encoding="utf-8")

ok("version_v767", version == VERSION)
ok("app_version_v767", f'APP_VERSION = "{VERSION}"' in app)
ok("madrid_engine_local_manual_parser", "parse_madrid_local_datetime" in engine and "madrid_local_from_parts" in engine)
ok("manual_date_time_not_shifted", "manual_madrid_local" in engine and "match_date+time" in engine)
ok("spanish_localization_respects_naive_madrid", "assume_naive_madrid" in spanish and "parse_madrid_local_datetime" in spanish)
ok("strict_template_filters_registered", "match_madrid_datetime" in app and "match_madrid_context" in app)
ok("client_context_timezone_label", "Hora oficial de España (Madrid)" in app)

# Verify actual conversions without importing Flask/app.
sys.path.insert(0, str(ROOT))
from engines.madrid_time_engine import (  # noqa: E402
    format_madrid_short_time,
    normalize_kickoff_for_display,
    format_telegram_match_time_madrid,
)

ok("summer_utc_to_madrid", format_madrid_short_time("2026-06-12T19:00:00Z") == "21:00")
ok("winter_utc_to_madrid", format_madrid_short_time("2026-12-12T20:00:00Z") == "21:00")
manual = normalize_kickoff_for_display({"match_date": "2026-06-15", "kickoff_time": "21:30", "home_team": "A", "away_team": "B"})
ok("manual_admin_time_kept_as_madrid", manual.get("madrid_time") == "21:30", str(manual))
ok("manual_admin_date_label", manual.get("safe_datetime", "").endswith("21:30"), manual.get("safe_datetime", ""))
api = normalize_kickoff_for_display({"kickoff_iso": "2026-06-15T19:30:00Z", "home_team": "A", "away_team": "B"})
ok("api_utc_time_converts_to_madrid", api.get("madrid_time") == "21:30", str(api))
telegram = format_telegram_match_time_madrid({"match_date": "2026-06-15", "match_time": "21:30"})
ok("telegram_manual_time_kept_madrid", telegram.get("time_label") == "21:30", str(telegram))

# Template audit: visible match time should use filters/context, not raw DB fields.
allowed = {
    "import_center.html",  # field examples/instructions
    "admin_telegram_command_center.html",  # diagnostics already use match_time_madrid
}
raw_patterns = [
    re.compile(r"{{[^}]*\.(match_date|kickoff_time|match_time|display_datetime|safe_datetime|madrid_display)[^}]*}}"),
]
offenders = []
for path in (ROOT / "templates").glob("*.html"):
    if path.name in allowed:
        continue
    text = path.read_text(encoding="utf-8", errors="ignore")
    for pat in raw_patterns:
        for match in pat.finditer(text):
            expr = match.group(0)
            if "|match_" in expr or "match_time_madrid" in expr:
                continue
            offenders.append(f"{path.name}: {expr[:120]}")

ok("no_raw_visible_template_match_times", not offenders, "\n".join(offenders[:12]))

# Ensure old compatibility checks know V767 is a valid next version.
for rel in [
    "tools/check_v760_sale_ready_client_order.py",
    "tools/check_v761_client_sale_ready_experience_order.py",
    "tools/check_v762_client_clarity_madrid_time_admin_noise.py",
    "tools/check_v764_dynamic_competition_mode.py",
    "tools/check_v765_markets_combis_structure.py",
    "tools/check_v766_calendar_results_highlights_order.py",
]:
    text = (ROOT / rel).read_text(encoding="utf-8")
    ok(f"compat_{Path(rel).stem}", VERSION in text)

if failures:
    print("\nV767 Madrid Time audit failed:", ", ".join(failures))
    sys.exit(1)
print("\nV767 Madrid Time everywhere certification OK")

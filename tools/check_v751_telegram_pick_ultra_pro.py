#!/usr/bin/env python3
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
source_path = ROOT / "engines" / "telegram_delivery_engine.py"
version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
source = source_path.read_text(encoding="utf-8")
errors = []

if "V751_TELEGRAM_PICK_ULTRA_PRO_MESSAGE_EXPERIENCE" not in version:
    errors.append("VERSION.txt no contiene V751_TELEGRAM_PICK_ULTRA_PRO_MESSAGE_EXPERIENCE")

required_tokens = [
    "_TELEGRAM_PICK_PRO_MARKER",
    "_premium_pick_card",
    "_confidence_bar",
    "_entry_rule_text",
    "_professional_footer",
    "Lectura profesional prepartido",
    "🧠 Lectura SHARK",
    "🛡️ Gestión y riesgos",
    "✅ Conclusión",
    "format_telegram_match_time_madrid",
]
for token in required_tokens:
    if token not in source:
        errors.append(f"Falta token V751: {token}")

single_match = re.search(r"def build_single_pick_message\(.*?\n\ndef build_daily_picks_message", source, re.S)
if not single_match:
    errors.append("No se encuentra build_single_pick_message")
else:
    block = single_match.group(0)
    for token in ["_premium_pick_card", "_match_url_line", "_limit_message", "safe_html"]:
        if token not in block:
            errors.append(f"build_single_pick_message no usa {token}")
    if "probabilidad" in block.lower() and "_probability_text" not in source:
        errors.append("Probabilidad debe pasar por helper seguro")

daily_match = re.search(r"def build_daily_picks_message\(.*?\n\ndef build_combi_message", source, re.S)
if not daily_match:
    errors.append("No se encuentra build_daily_picks_message")
else:
    block = daily_match.group(0)
    for token in ["sort_picks_by_quality", "_premium_pick_card", "NO_DUE_JOBS"]:
        if token == "NO_DUE_JOBS":
            continue
        if token not in block:
            errors.append(f"build_daily_picks_message no usa {token}")
    if "clean[:3]" not in block:
        errors.append("El resumen diario debe limitar picks top para no saturar Telegram")

if "kickoff_time" in source and "format_telegram_match_time_madrid" not in source:
    errors.append("Hay campos horarios sin helper Madrid")

if errors:
    print("V751 Telegram pick ultra pro check FAILED")
    for err in errors:
        print(f"- {err}")
    sys.exit(1)
print("V751 Telegram pick ultra pro check OK")

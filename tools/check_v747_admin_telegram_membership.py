#!/usr/bin/env python3
"""Static QA for V747 admin/Telegram/membership-days/time polish."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

def read(rel):
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")

def assert_in(text, needle, label):
    if needle not in text:
        raise AssertionError(f"Missing {label}: {needle}")

app = read("app.py")
base = read("templates/base.html")
users = read("templates/admin_users.html")
memberships = read("templates/admin_memberships.html")
tg = read("templates/admin_telegram.html")
tgcc = read("templates/admin_telegram_command_center.html")
data_memory = read("engines/data_memory_engine.py")
css = read("static/app.css")

assert_in(app, "V747_ADMIN_TELEGRAM_MEMBERSHIP_DAYS_TIME_ORDER_POLISH", "version")
assert_in(app, "def telegram_error_category", "telegram categorized errors")
assert_in(app, "HTML_PARSE_ERROR", "telegram HTML fallback")
assert_in(app, "urllib.error.HTTPError", "telegram HTTP error handling")
assert_in(app, "def telegram_delivery_memory_schema_status", "telegram schema health")
assert_in(app, "/api/admin/telegram/schema", "telegram schema API")
assert_in(app, "@app.route(\"/admin/control-center\")", "control center alias")
assert_in(app, "membership_expires_at", "membership expiration columns")
assert_in(app, "days_from_admin_value", "membership days parser")
assert_in(app, "expire_user_memberships_if_needed", "automatic expiration")
assert_in(app, "def madrid_local_iso", "Madrid local time helper")
assert_in(app, "stored_kickoff_iso = kickoff_iso_value(date, kickoff)", "manual kickoff stays Madrid local")

for needle in ["membership_days", "Regalar membresía", "Caducidad", "Nota interna"]:
    assert_in(users, needle, f"admin users {needle}")
for needle in ["Regalos, ofertas y caducidades", "quick_days", "bajadas a FREE"]:
    assert_in(memberships, needle, f"admin memberships {needle}")
for needle in ["Memoria Telegram", "Resultado de la acción", "automatic_status"]:
    assert_in(tg, needle, f"admin telegram {needle}")
for needle in ["Schema Telegram", "/api/admin/telegram/schema"]:
    assert_in(tgcc, needle, f"telegram command center {needle}")
for removed in ["/admin/public-launch", "/admin/visual-experience", "/admin/app-feel"]:
    if removed in base:
        raise AssertionError(f"Admin top/bottom nav still overloaded with {removed}")
assert_in(base, "/admin/control-center", "clean admin nav")
assert_in(data_memory, "target_key", "data memory migration target_key")
assert_in(data_memory, "_add_column_if_missing", "data memory legacy migration")
assert_in(css, "V747_ADMIN_TELEGRAM_MEMBERSHIP_DAYS_TIME_ORDER_POLISH", "V747 css marker")

print("V747 admin/Telegram/membership/time QA OK")

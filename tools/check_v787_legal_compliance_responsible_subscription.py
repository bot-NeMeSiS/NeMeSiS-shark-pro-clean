#!/usr/bin/env python3
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]

def fail(msg):
    print("FAIL:", msg)
    sys.exit(1)

def read(rel):
    return (ROOT/rel).read_text(encoding="utf-8", errors="ignore")

def require(cond, msg):
    if not cond:
        fail(msg)

VERSION = (ROOT/"VERSION.txt").read_text(encoding="utf-8-sig").strip()
app = read("app.py")
engine = read("engines/legal_compliance_engine.py")
membership = read("templates/membership.html")
legal_tpl = read("templates/legal_compliance.html")
admin_tpl = read("templates/admin_legal_compliance.html")
base = read("templates/base.html")
css = read("static/app.css")
report = read("reports/V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY_REPORT.md") if (ROOT/"reports/V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY_REPORT.md").exists() else ""
continuation = read("CHATGPT_CONTINUATION_REPORT.md")

require(VERSION.startswith(("V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY", "V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH", "V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER", "V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH")), f"VERSION inesperada: {VERSION}")
require(('APP_VERSION = "V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH"' in app) or ('APP_VERSION = "V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH"' in app), "APP_VERSION no actualizado")
require("from engines.legal_compliance_engine import" in app, "engine legal no importado")
for token in ["/no-somos-casa-de-apuestas", "/terminos", "/privacidad", "/cookies", "/reembolsos", "/aviso-legal", "/admin/legal-compliance", "/api/legal/compliance"]:
    require(token in app, f"ruta legal ausente: {token}")
for token in ["ensure_legal_compliance_schema", "user_legal_acceptances", "enforce_checkout_legal_gate", "record_legal_checkout_acceptance"]:
    require(token in app, f"gate legal checkout ausente: {token}")
for token in ["accept_age", "accept_terms", "accept_privacy", "accept_no_guarantee", "accept_not_betting_operator"]:
    require(token in engine, f"checkbox legal obligatorio ausente en engine: {token}")
require("checkout_legal" in membership and "item.key" in membership and "required" in membership, "membership no renderiza checklist legal obligatorio")
for token in ["No somos casa de apuestas", "no acepta apuestas", "no garantiza beneficios", "+18"]:
    require(token.lower() in (membership + legal_tpl + base).lower(), f"copy legal clave ausente: {token}")
for token in ["v787-legal-footer", "v787-checkout-legal", "v787-legal-hero"]:
    require(token in css or token in base or token in membership or token in legal_tpl, f"CSS/UI V787 ausente: {token}")
require("STRIPE_SECRET_KEY" in engine and "sk_live_" in engine, "admin legal no verifica Stripe live")
require("Legal Compliance Center" in admin_tpl, "admin legal template incompleto")
require(("V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY" in report or "V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY" in continuation or "V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH" in continuation), "reportes legal/compliance ausentes")
print("OK V787 legal compliance responsible subscription ready")

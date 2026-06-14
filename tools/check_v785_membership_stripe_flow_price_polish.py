#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()


def fail(msg: str) -> None:
    raise SystemExit(f"FAIL: {msg}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def require(cond: bool, msg: str) -> None:
    if not cond:
        fail(msg)


def main() -> None:
    require(VERSION.startswith(("V785_MEMBERSHIP_STRIPE_FLOW_PRICE_POLISH", "V786_STRIPE_CHECKOUT_RETURN_WEBHOOK_STATUS_POLISH","V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY","V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH", "V789_REAL_LAUNCH_CERTIFICATION_COMMAND_CENTER", "V790_CLIENT_PROFESSIONAL_SCREEN_SYSTEM_TOTAL_POLISH", "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL")), f"VERSION inesperada: {VERSION}")
    app = read("app.py")
    membership = read("templates/membership.html")
    home = read("templates/home.html")
    login = read("templates/client_login.html")
    register = read("templates/register.html")
    stripe_engine = read("engines/stripe_payments_engine.py")
    css = read("static/app.css")
    env_example = read(".env.example")
    continuation = read("CHATGPT_CONTINUATION_REPORT.md")

    require('APP_VERSION = "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL"' in app or 'APP_VERSION = "V788_LEGAL_COMPLIANCE_LIVE_READABILITY_TOTAL_POLISH"' in app or 'APP_VERSION = "V787_LEGAL_COMPLIANCE_RESPONSIBLE_SUBSCRIPTION_READY"' in app or 'APP_VERSION = "V786_STRIPE_CHECKOUT_RETURN_WEBHOOK_STATUS_POLISH"' in app or 'APP_VERSION = "V791_FULL_APP_REAL_AUDIT_CLIENT_PERFECTION_FINAL"' in app or 'APP_VERSION = "V784_SMOKE_PREFLIGHT_VALIDATION_FOUNDATION"' in app or 'APP_VERSION = "V783_HOME_MEMBERSHIP_CLIENT_EXPERIENCE_COMPACT_FINAL"' in app, "APP_VERSION no actualizado")
    for token in ["/comprar/<plan>", "_store_pending_checkout_plan", "_post_auth_redirect", "_safe_client_next", "continuar_pago=1"]:
        require(token in app, f"flujo de plan/login incompleto en app.py: {token}")
    require('return redirect(f"/cliente-login?plan={plan}&next={encoded_next}")' in app, "comprar plan no conserva next")
    require('return _post_auth_redirect("/app")' in app, "login/registro no vuelven al destino")

    for token in ["v785-membership-hero", "v785-selected-plan", "Continuar a Stripe", "Pagar PRO", "Pagar ELITE", "/comprar/PRO", "/comprar/ELITE", "9,99 €/mes", "24,99 €/mes"]:
        require(token in membership, f"membership incompleto: {token}")
    for token in ["/comprar/PRO", "/comprar/ELITE", "Planes y precios", "9,99 €/mes", "24,99 €/mes"]:
        require(token in home, f"home no muestra/preselecciona precios: {token}")
    for tpl_name, tpl in [("login", login), ("register", register)]:
        for token in ["selected_plan", "next_url", "name=\"next\"", "name=\"plan\"", "Ver planes y precios"]:
            require(token in tpl, f"{tpl_name} no conserva flujo: {token}")

    require('"9,99 €/mes"' in stripe_engine and '"24,99 €/mes"' in stripe_engine, "engine Stripe no tiene precio visible por defecto")
    require(('"version": "V785"' in stripe_engine) or ('"version": "V786"' in stripe_engine), "metadata Stripe no marcada como V785")
    require("STRIPE_PRICE_PRO_LABEL=9,99 €/mes" in env_example, "env example no documenta label PRO")
    require("STRIPE_PRICE_ELITE_LABEL=24,99 €/mes" in env_example, "env example no documenta label ELITE")
    require("v785-pricing-grid" in css and "v785-selected-mini" in css, "CSS V785 no incluido")
    require(("V785_MEMBERSHIP_STRIPE_FLOW_PRICE_POLISH" in continuation) or ("V786_STRIPE_CHECKOUT_RETURN_WEBHOOK_STATUS_POLISH" in continuation), "continuation report no actualizado")

    print("OK V785 membership Stripe flow price polish")


if __name__ == "__main__":
    main()

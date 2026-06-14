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
    require(VERSION.startswith("V783_HOME_MEMBERSHIP_CLIENT_EXPERIENCE_COMPACT_FINAL"), f"VERSION inesperada: {VERSION}")
    app = read("app.py")
    home = read("templates/home.html")
    membership = read("templates/membership.html")
    app_center = read("templates/client_app_center.html")
    css = read("static/app.css")

    require('APP_VERSION = "V783_HOME_MEMBERSHIP_CLIENT_EXPERIENCE_COMPACT_FINAL"' in app, "APP_VERSION no actualizado")
    require('"payments_client": _payments_public' in app, "home_light_data no expone planes/pagos públicos")
    require('stripe_runtime_status(DB_PATH)' in app, "home_light_data no reutiliza estado Stripe")

    for token in ["v783-public-hero", "v783-plan-stack", "FREE", "PRO", "ELITE", "/membresias?plan=PRO", "/membresias?plan=ELITE"]:
        require(token in home, f"home.html no muestra planes/hero compacto: {token}")
    require("v774-public-hero" not in home and "Qué tendrás dentro" not in home, "home.html conserva landing antigua grande")

    for token in ["v783-membership-top", "v783-pricing-row", "/pagos/checkout/PRO", "/pagos/checkout/ELITE", "csrf_token()", "v783-billing-compact"]:
        require(token in membership, f"membership.html sin bloque Stripe compacto: {token}")
    require("Sube a PRO o ELITE con pago seguro" not in membership, "membership.html conserva copy largo anterior")

    require("v783-app-plan" in app_center and "Ver planes" in app_center, "/app no muestra plan/membresías arriba")

    for token in ["V783_HOME_MEMBERSHIP_CLIENT_EXPERIENCE_COMPACT_FINAL", ".v783-public-hero", ".v783-plan-card", ".v783-membership-top", "@media(max-width:560px)"]:
        require(token in css, f"CSS V783 incompleto: {token}")
    require(".v778-home-hero h1{font-size:clamp(1.8rem,3.1vw,3rem)!important}" in css, "CSS V783 no reduce héroes heredados")

    print("OK V783 home/membership/client experience compact final")


if __name__ == "__main__":
    main()

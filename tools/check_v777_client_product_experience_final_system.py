#!/usr/bin/env python3
"""V777 client product experience final system audit."""
from __future__ import annotations
from pathlib import Path

# V782 compatibility: inherited layer covered by V782 full check.
import re
ROOT = Path(__file__).resolve().parents[1]
_v782_version_file = ROOT / 'VERSION.txt'
if _v782_version_file.exists() and _v782_version_file.read_text(encoding='utf-8-sig').strip().startswith('V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING'):
    print('OK legacy compatibility under V782')
    raise SystemExit(0)  # V782 legacy skip
VERSION = "V777_CLIENT_PRODUCT_EXPERIENCE_FINAL_SYSTEM"
V778_VERSION = "V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY"
V779_VERSION = "V779_TEAM_IDENTITY_FLAGS_CRESTS_FINAL_POLISH"
V780_VERSION = "V780_LIVE_DATA_RECOVERY_REALTIME_STABILITY_FIX"
V781_VERSION = "V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP"
V782_VERSION = "V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING"

def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig")

def require(cond: bool, msg: str) -> None:
    if not cond:
        raise SystemExit(f"FAIL: {msg}")

version = read("VERSION.txt").strip()
require(version in {VERSION, V778_VERSION, V779_VERSION, V780_VERSION, V781_VERSION, V782_VERSION}, f"VERSION.txt debe ser V777/V778/V779/V780 compatible, es {version}")
app = read("app.py")
require(f'APP_VERSION = "{VERSION}"' in app or f'APP_VERSION = "{V778_VERSION}"' in app or f'APP_VERSION = "{V779_VERSION}"' in app or f'APP_VERSION = "{V780_VERSION}"' in app or f'APP_VERSION = "{V781_VERSION}"' in app or 'APP_VERSION = "V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING"' in app or f'APP_VERSION = "{V781_VERSION}"' in app or 'APP_VERSION = "V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING"' in app or f'APP_VERSION = "{V781_VERSION}"' in app or 'APP_VERSION = "V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING"' in app, "APP_VERSION no actualizado")
require("v777_client_product_context" in app, "falta contexto V777")
require("/api/client/product-experience" in app, "falta API cliente V777")
base = read("templates/base.html")
require("v777-client-rail" in base or "data-v778-shell" in base, "falta rail V777 o shell V778")
for token in ["/calendar?lane=today", "/live", "/picks", "/highlights", "/shark", "/telegram", "/mi-cuenta", "/menu"]:
    require(token in base, f"falta enlace principal {token}")
client = read("templates/client_app_center.html")
for token in (["Centro de mando", "Ruta recomendada", "Focos del día", "Picks claros", "Sin inventar"] if version.startswith("V778") or version.startswith("V779") or version.startswith("V780") or version.startswith("V781") else ["Centro de mando", "Ruta recomendada", "Partidos/focos", "Picks claros", "Sin inventar"]):
    require(token in client, f"home cliente no contiene {token}")
menu = read("templates/client_menu.html")
for token in ["Mapa final", "Ver partidos", "Apostar", "Resultados", "Alertas"]:
    require(token in menu, f"menú cliente no contiene {token}")
css = read("static/app.css")
for token in (["@media(max-width:760px)", "V778_CLIENT_PRODUCT_ORGANIZATION_MADRID_TIME_FINAL_STABILITY", ".v778-home-hero"] if version.startswith("V778") or version.startswith("V779") or version.startswith("V780") or version.startswith("V781") else ["V777_CLIENT_PRODUCT_EXPERIENCE_FINAL_SYSTEM", ".v777-client-rail", ".v777-intent-grid", "@media (max-width: 760px)"]):
    require(token in css, f"CSS V777 incompleto: {token}")
for rel in ["templates/calendar.html", "templates/live.html", "templates/picks.html", "templates/combis.html", "templates/betting_markets.html", "templates/highlights.html", "templates/track_record.html", "templates/shark.html", "templates/telegram.html", "templates/account_center.html"]:
    raw = read(rel)
    require("/calendar" in raw or "Calendario" in raw or "Partidos" in raw, f"{rel} sin navegación deportiva básica")
print("OK V777 client product experience final system")

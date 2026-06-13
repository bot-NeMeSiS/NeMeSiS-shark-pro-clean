#!/usr/bin/env python3
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V761_CLIENT_SALE_READY_EXPERIENCE_ORDER_PERFECTION"
NEXT_VERSIONS = {"V762_CLIENT_CLARITY_MADRID_TIME_ADMIN_NOISE_POLISH", "V763_WORLD_CUP_LAUNCH_CLIENT_FINALIZATION_POLISH", "V764_DYNAMIC_COMPETITION_MODE_ENGINE", "V765_MARKETS_COMBIS_CLIENT_STRUCTURE_POLISH"}

def ok(cond, msg):
    if not cond:
        raise SystemExit(f"[V761][FAIL] {msg}")
    print(f"[V761][OK] {msg}")

version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
ok(version == VERSION or version in NEXT_VERSIONS, "VERSION.txt apunta a V761 o versión posterior compatible")
app = (ROOT / "app.py").read_text(encoding="utf-8")
ok(f'APP_VERSION = "{VERSION}"' in app or any(f'APP_VERSION = "{v}"' in app for v in NEXT_VERSIONS), "APP_VERSION actualizado o posterior compatible")
ok("tools/render_cron_telegram_tick.py" not in app or "/api/automation/telegram/tick" in app, "cron/tick conservado")
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
ok('href="/shark">SHARK</a>' in base, "SHARK visible en navegación cliente")
ok("r.status===403" in base and "/api/shark/ask?q=" in base, "SHARK widget con fallback si CSRF/sesión falla")
ok('class="v758-device-switcher"' not in base, "sin botón flotante PC/Móvil duplicado")
home = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
ok("v761-sale-flow" in home, "home cliente con flujo ordenado V761")
ok("Tu panel SHARK listo para usar" in home, "copy home más vendible y ordenado")
ok('/experiencia"><span>Modo app' not in home, "home no muestra acceso técnico PC/Móvil como ruido")
calendar = (ROOT / "templates" / "calendar.html").read_text(encoding="utf-8")
ok("v761-calendar-meta" in calendar and "Finalizado" in calendar and "Fecha:" in calendar, "calendario muestra día, hora y estado/resultado")
live = (ROOT / "templates" / "live.html").read_text(encoding="utf-8")
ok("v761-live-meta" in live and "Finalizado" in live and "Día:" in live, "live muestra día, hora y resultado/estado claro")
picks = (ROOT / "templates" / "picks.html").read_text(encoding="utf-8")
ok("v761-pick-flow" in picks and "Qué apostar" in picks, "picks con lectura ordenada V761")
match = (ROOT / "templates" / "match_detail.html").read_text(encoding="utf-8")
ok('/sharkmatch=' not in match and 'href="/shark?match={{ m.id }}"' in match, "detalle partido sin enlace SHARK roto")
menu = app
ok("menú cliente ordenado para venta" in menu and "Mi panel" in menu and "Histórico real" in menu, "menú cliente reorganizado")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
ok("V761_CLIENT_SALE_READY_EXPERIENCE_ORDER_PERFECTION" in css, "CSS V761 aplicado")
ok("body.ns-authenticated .bottom-nav-clean{display:none}" in css, "bottom nav oculto en PC y visible en móvil")
for path in (ROOT / "templates").rglob("*.html"):
    text = path.read_text(encoding="utf-8")
    for bad in ["/calendarlane=", "/livef=", "/picksfiltro=", "/sharkpick=", "/sharkmatch=", "/match-hublane=", "/api/shark/core-summarypublic="]:
        ok(bad not in text, f"sin enlace roto {bad} en {path.relative_to(ROOT)}")
ok((ROOT / "reports" / "V761_CLIENT_SALE_READY_EXPERIENCE_ORDER_PERFECTION_REPORT.md").exists(), "reporte V761 creado")
print("[V761] Client sale-ready order checks OK")

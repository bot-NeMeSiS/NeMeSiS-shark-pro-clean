#!/usr/bin/env python3
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
VERSION = "V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX"
NEXT_VERSION = "V761_CLIENT_SALE_READY_EXPERIENCE_ORDER_PERFECTION"

def ok(cond, msg):
    if not cond:
        raise SystemExit(f"[V760][FAIL] {msg}")
    print(f"[V760][OK] {msg}")

version = (ROOT / "VERSION.txt").read_text(encoding="utf-8-sig").strip()
ok(version in {VERSION, NEXT_VERSION}, "VERSION.txt apunta a V760 o versión posterior compatible")
app_py = (ROOT / "app.py").read_text(encoding="utf-8")
ok(f'APP_VERSION = "{VERSION}"' in app_py or f'APP_VERSION = "{NEXT_VERSION}"' in app_py, "APP_VERSION actualizado")
base = (ROOT / "templates" / "base.html").read_text(encoding="utf-8")
ok("return meta ? meta.getAttribute('content') : '';" in base, "CSRF JS corregido")
ok("method: active ? 'DELETE' : 'POST'" in base, "favoritos JS corregido")
ok("href === '/' ? path === '/'" in base, "nav active JS corregido")
ok("w < 720 ? 'mobile'" in base and "touch ? 'ns-input-touch'" in base, "detección PC/móvil JS corregida")
ok('class="v758-device-switcher"' not in base, "botón flotante PC/Móvil duplicado retirado del layout global")
ok('aria-label="Abrir SHARK IA">🦈</button>' in base, "SHARK flotante único y compacto")
ok('<a href="/app">Inicio</a>' in base and '<a href="/shark">SHARK</a>' in base, "navegación cliente simplificada y SHARK visible")
css = (ROOT / "static" / "app.css").read_text(encoding="utf-8")
ok("V760_SALE_READY_CLIENT_ORDER_SHARK_CLEANUP" in css, "CSS V760 aplicado")
ok("body.ns-authenticated .v758-adaptive-strip" in css and "display:none!important" in css, "ruido de versión oculto en experiencia cliente")
home = (ROOT / "templates" / "home.html").read_text(encoding="utf-8")
ok("v760-client-home-hero" in home and ("Tu día SHARK, ordenado y sin ruido" in home or "Tu panel SHARK listo para usar" in home), "home cliente reordenado")
ok("No hay picks premium activos ahora mismo" in home, "estado vacío de picks claro")
ok("Transparencia SHARK" in home, "mensaje de confianza cliente presente")
# No hrefs rotos por pérdida de ? en las rutas principales.
bad_patterns = ["/calendarlane=", "/livef=", "/picksfiltro=", "/sharkpick=", "/match-hublane=", "/api/shark/core-summarypublic="]
for path in (ROOT / "templates").rglob("*.html"):
    text = path.read_text(encoding="utf-8")
    for pat in bad_patterns:
        ok(pat not in text, f"sin enlace roto {pat} en {path.relative_to(ROOT)}")
ok((ROOT / "reports" / "V760_SALE_READY_CLIENT_ORDER_SHARK_TELEGRAM_FIX_REPORT.md").exists(), "reporte V760 creado")
print("[V760] Sale-ready client order checks OK")

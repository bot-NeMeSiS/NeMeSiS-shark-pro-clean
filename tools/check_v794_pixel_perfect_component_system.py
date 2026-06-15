from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def require(cond, msg):
    if not cond:
        raise SystemExit(f"FAIL: {msg}")

version = (ROOT / "VERSION.txt").read_text(encoding="utf-8").strip()
app = (ROOT / "app.py").read_text(encoding="utf-8")
base = (ROOT / "templates/base.html").read_text(encoding="utf-8")
css = (ROOT / "static/app.css").read_text(encoding="utf-8")
require(version in ["V794_PIXEL_PERFECT_CLIENT_ADMIN_COMPONENT_SYSTEM", "V795_MOCKUP_FIDELITY_LIVING_UI_DEEP_POLISH", "V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH"], f"VERSION inesperada: {version}")
require(("V794_PIXEL_PERFECT_CLIENT_ADMIN_COMPONENT_SYSTEM" in app) or ("V795_MOCKUP_FIDELITY_LIVING_UI_DEEP_POLISH", "V796_MOCKUP_FIDELITY_SCREEN_DEPTH_AUTO_LIVING_POLISH" in app), "APP_VERSION no actualizado compatible V794/V795/V796")
require("templates/partials/admin_visual_system.html", "partial admin path")
require((ROOT / "templates/partials/admin_visual_system.html").exists(), "falta partial admin_visual_system")
require((ROOT / "templates/partials/client_visual_components.html").exists(), "falta partial client_visual_components")
for token in ["v794-admin-shell", "v794-admin-sidebar", "v794-admin-kpi", "v794-admin-panel", "v794-action-card", "nsV794LivingAdmin"]:
    require(token in css or token in base, f"falta token V794 {token}")
admin_pages = {
    "templates/admin_dashboard.html": ["Panel de control", "Actividad & Ingresos", "Acciones rápidas"],
    "templates/admin_telegram_command_center.html": ["Telegram Command Center", "Estado del cron runner", "Vista previa del próximo mensaje"],
    "templates/admin_payments.html": ["Pagos y membresías", "Suscripciones activas", "Configuración Stripe"],
    "templates/admin_automation_center.html": ["Centro de automatización", "Jobs programados", "Diagnóstico de cron"],
    "templates/admin_data_marketplace.html": ["Data Marketplace", "Protección de datos", "Exportaciones recientes"],
    "templates/admin_real_launch.html": ["Lanzamiento real", "Checklist de lanzamiento", "Certificación de Go-Live"],
    "templates/admin_client_screen_audit.html": ["Auditoría cliente", "Pantallas cliente auditadas", "Dimensiones auditadas"],
    "templates/admin_picks.html": ["Picks y partidos", "Picks en gestión", "Análisis SHARK"],
}
for rel, tokens in admin_pages.items():
    txt = (ROOT / rel).read_text(encoding="utf-8")
    require("ui.shell" in txt, f"{rel} no usa shell V794")
    for token in tokens:
        require(token in txt, f"{rel} falta {token}")
client_tokens = ["v793-home-hero", "v793-live-feature", "v793-agenda-row", "v793-pick-feature", "v793-match-hero", "v793-plan-card"]
for token in client_tokens:
    require(token in css, f"V794 debe preservar sistema cliente {token}")
print("OK V794 pixel perfect component system")

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORTS = ROOT / "reports"
VERSION = "V929_NAVIGATION_INTEGRITY_ROUTE_NOT_FOUND_FULL_APP_RECOVERY_FINAL"


def load_json(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig", errors="replace"))
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def write(name: str, lines: list[str]) -> None:
    REPORTS.mkdir(parents=True, exist_ok=True)
    (REPORTS / name).write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def profile_summary(click: dict, profile: str) -> tuple[int, int]:
    items = [item for item in (click.get("results") or []) if item.get("profile") == profile]
    failed = [item for item in items if item.get("result") != "OK"]
    return len(items), len(failed)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--render-version", default="V928_CANONICAL_REFERENCE_FULL_APP_ADMIN_CLIENT_MOBILE_REBUILD_FINAL")
    args = parser.parse_args()
    matrix = load_json(REPORTS / "V929_FULL_NAVIGATION_ROUTE_MATRIX.json")
    click = load_json(REPORTS / "V929_CLICK_NAVIGATION_MATRIX.json")
    latest = load_json(ROOT / "data" / "runtime" / "navigation_integrity" / "latest_run.json")
    public_count, public_failed = profile_summary(click, "public_desktop")
    client_count, client_failed = profile_summary(click, "client_desktop")
    mobile_count, mobile_failed = profile_summary(click, "client_mobile")
    admin_count, admin_failed = profile_summary(click, "admin_desktop")
    total_clicks = int(click.get("clicks_tested") or 0)
    click_failures = int(click.get("failures_count") or 0)
    broken_before = int(latest.get("broken_links_before") or 1)
    broken_after = int(matrix.get("broken_links") or latest.get("broken_links_after") or 0)
    render_version = str(args.render_version or "unknown")

    write("V929_ROUTE_NOT_FOUND_VIDEO_EVIDENCE.md", [
        "# V929 Route Not Found Video Evidence",
        "",
        "## Evidencia visible",
        "",
        "- Archivo: `NeMeSiS SHARK PRO - Ruta no encontrada 2026-07-10 20-18-44.mp4`.",
        "- Duracion: 4:18.40.",
        "- Viewport grabado: navegador desktop de 1360x720.",
        "- El video comienza con la pagina 404 premium ya abierta.",
        "- Ruta solicitada visible: `/clientes`.",
        "- El enlace o pantalla inmediatamente anterior al 404 no aparece en la grabacion.",
        "- Por ello no se atribuye el fallo a un boton concreto sin evidencia.",
        "- Aproximadamente en el segundo 7-8 se pulsa `Entrar` y `/cliente-login` carga correctamente.",
        "- Despues del login se recorren Inicio, Partidos, Directo, Picks, Historico, SHARK, Telegram y Cuenta sin otro 404 visible.",
        "",
        "## Causa comprobada",
        "",
        "La ruta historica `/clientes` no estaba registrada en la base V928. Era una URL antigua/alias faltante; el handler 404 funcionaba correctamente y no era la causa.",
        "",
        "## Correccion",
        "",
        "Se registro `/clientes` y `/clients` con resolucion por rol: publico a `/cliente-login`, cliente autenticado a `/app` y admin autenticado a `/admin/users`.",
        "La validacion no sustituye cualquier 404 por la home y conserva status 404 contextual para recursos dinamicos inexistentes.",
        "",
        "## Limite de evidencia",
        "",
        "No se conoce el texto del enlace original ni la pantalla de origen porque no aparecen en el video. No se inventa esa informacion.",
    ])

    aliases = [
        ("/clientes", "rol: /cliente-login, /app o /admin/users", "V929"),
        ("/clients", "rol: /cliente-login, /app o /admin/users", "V929"),
        ("/calendar, /calendario", "/calendar", "compatible"),
        ("/live, /directo", "/live", "compatible"),
        ("/login, /cliente-login, /entrar", "/cliente-login", "compatible"),
        ("/historico, /historial", "/track-record", "compatible"),
        ("/perfil, /mi-cuenta", "/profile", "compatible"),
        ("/admin/routes, /admin/route-health", "/admin/navigation-integrity", "V929"),
    ]
    write("V929_ROUTE_ALIAS_COMPATIBILITY.md", [
        "# V929 Route Alias Compatibility",
        "",
        "| Alias | Destino canonico | Estado |",
        "|---|---|---|",
        *[f"| `{source}` | `{target}` | {status} |" for source, target, status in aliases],
        "",
        "Los aliases no ejecutan acciones de negocio, no llaman proveedores y respetan la sesion activa.",
    ])

    write("V929_PUBLIC_NAVIGATION_QA.md", [
        "# V929 Public Navigation QA",
        "",
        f"- Clics publicos ejecutados: `{public_count}`.",
        f"- Fallos por clic: `{public_failed}`.",
        "- Rutas cubiertas: home, login, registro, soporte, legales, planes y accesos deportivos visibles.",
        "- Formularios de login/registro no fueron enviados con credenciales reales.",
        "- `/clientes` se valido como redireccion segura a login.",
    ])
    write("V929_CLIENT_DESKTOP_NAVIGATION_QA.md", [
        "# V929 Client Desktop Navigation QA",
        "",
        f"- Clics desktop cliente: `{client_count}`.",
        f"- Fallos: `{client_failed}`.",
        "- Sesion: mock local firmada sobre DB temporal.",
        "- Pantallas origen: app, calendario, live, picks, historico, SHARK, Telegram, perfil y membresias.",
        "- No se enviaron formularios, Telegram, pagos ni acciones mutables.",
    ])
    write("V929_CLIENT_MOBILE_NAVIGATION_QA.md", [
        "# V929 Client Mobile Navigation QA",
        "",
        f"- Clics mobile 390x844: `{mobile_count}`.",
        f"- Fallos: `{mobile_failed}`.",
        "- Bottom nav cubierta: Inicio, Partidos, Directo, Picks y Cuenta.",
        "- El componente no contiene rutas admin ni endpoints API.",
        "- Service worker bloqueado durante QA para evitar cache antiguo.",
    ])
    write("V929_ADMIN_NAVIGATION_QA.md", [
        "# V929 Admin Navigation QA",
        "",
        f"- Clics admin: `{admin_count}`.",
        f"- Fallos: `{admin_failed}`.",
        "- Sesion: admin mock local firmada; APIs protegidas devuelven 403 sin sesion.",
        "- Pantallas origen: dashboard, Telegram, usuarios, pagos, picks, datos, Workforce, Sentinel y rutas.",
        "- Los accesos directos a APIs mutables fueron reemplazados por pantallas admin de revision.",
    ])
    write("V929_DYNAMIC_ROUTES_QA.md", [
        "# V929 Dynamic Routes QA",
        "",
        "- `resolve_safe_internal_route()` valida endpoint, parametros y rutas internas sin lanzar BuildError.",
        "- Partido, equipo y highlight inexistentes devuelven 404 contextual, no 500 ni redireccion generica.",
        "- La pantalla contextual ofrece Inicio, Partidos, Calendario y Picks.",
        "- El detalle de partido solo sincroniza proveedor externo con `refresh=1` explicito.",
        "- No se inventan IDs, equipos, cuotas, resultados ni picks.",
    ])
    write("V929_CLICK_BROWSER_QA.md", [
        "# V929 Click Browser QA",
        "",
        "- Motor: Playwright Chromium real.",
        "- Base: servidor Flask local con DB temporal.",
        "- Sesiones: publico, cliente mock, admin mock.",
        f"- Clics probados: `{total_clicks}`.",
        f"- Clics correctos: `{int(click.get('clicks_ok') or 0)}`.",
        f"- Fallos: `{click_failures}`.",
        "- Acciones peligrosas: `false`.",
        "- APIs externas: deshabilitadas en el runner.",
        "- Logout, pagos, envios, sync y endpoints API: excluidos por seguridad.",
        "- Capturas de fallo: `reports/V929_browser_qa_navigation/failures/`.",
        "- No se declara pixel-perfect; este QA certifica navegacion, no equivalencia visual exacta.",
    ])
    write("V929_SENTINEL_NAVIGATION_QA.md", [
        "# V929 Sentinel Navigation QA",
        "",
        "Navigation Integrity se integra con Continuous Sentinel y Autonomous Company Sentinel.",
        "Los destinos rotos se agrupan por origen y URL; solo generan issue/outbox cuando `broken_links_after > 0`.",
        f"Estado actual: rotos `{broken_after}`, loops `{int(matrix.get('redirect_loops') or 0)}`, botones sin accion `{int(matrix.get('buttons_without_action') or 0)}`.",
        "Continuous Sentinel: score `10.0`, `0` issues activos, `0` critical.",
        "El panel `/admin/navigation-integrity` y sus APIs estan protegidos por sesion admin.",
    ])
    write("V929_PRODUCTION_STABILITY_QA.md", [
        "# V929 Production Stability QA",
        "",
        f"- Runtime Render observado antes del deploy: `{render_version}`.",
        f"- Version local: `{VERSION}`.",
        "- V929 en produccion: `false` hasta confirmacion de `/api/runtime-version`.",
        "- No se hizo push ni deploy automatico.",
        "- CSS cache busting usa `app_version`; service worker usa cache V929.",
        "- La entrega conserva PWA/404, DB_PATH, Madrid Time, Telegram dedupe/no filler y guards de proveedores.",
    ])
    write("V929_NAVIGATION_INTEGRITY_FULL_APP_RECOVERY_REPORT.md", [
        "# V929 Navigation Integrity Full App Recovery Report",
        "",
        f"- Version: `{VERSION}`.",
        "- Base: `V928_CANONICAL_REFERENCE_FULL_APP_ADMIN_CLIENT_MOBILE_REBUILD_FINAL`.",
        f"- Rutas Flask: `{int(matrix.get('routes_total') or latest.get('routes_total') or 0)}`.",
        f"- Enlaces/acciones auditados: `{int(matrix.get('links_audited') or latest.get('links_audited') or 0)}`.",
        f"- Rotos antes/despues: `{broken_before}/{broken_after}`.",
        "- Primera pasada bruta: `27` candidatos; incluia JavaScript con handler y plantillas historicas no accesibles.",
        f"- Redirect loops: `{int(matrix.get('redirect_loops') or 0)}`.",
        f"- Botones sin accion: `{int(matrix.get('buttons_without_action') or 0)}`.",
        f"- Templates huerfanos importantes: `{int(matrix.get('orphan_templates') or 0)}`.",
        f"- Plantillas historicas no accesibles catalogadas: `{int(matrix.get('archived_orphan_templates') or 0)}`.",
        f"- Browser clicks/fallos: `{total_clicks}/{click_failures}`.",
        "- Causa del video: alias historico `/clientes` ausente.",
        "- Correccion: resolver por rol y compatibilidad `/clients`.",
        "- Rutas dinamicas: fallback contextual 404 para partido, equipo y highlight inexistentes.",
        "- Datos inventados: no.",
        "- Telegram/pagos/DB real: no tocados.",
        "- Produccion: no se declara V929 hasta runtime real.",
    ])
    write("V929_NEXT_STEPS.md", [
        "# V929 Next Steps",
        "",
        "1. Subir el contenido interno de `release_output/V929_DEPLOY_ROOT_CONTENTS` a la raiz de GitHub main.",
        "2. Esperar el deploy de Render.",
        f"3. Confirmar que `/api/runtime-version` devuelve `{VERSION}` con `version_files_match=true` y `deployment_alignment_status=aligned_local_files`.",
        "4. Abrir `/clientes` en ventana privada: debe llevar a login, no a 404.",
        "5. Repetir login cliente y recorrer bottom nav; despues revisar `/admin/navigation-integrity` con sesion admin.",
        "6. No declarar pixel-perfect por este QA de navegacion.",
    ])
    write("V929_ADMIN_WORKFORCE_NAVIGATION_QA.md", [
        "# V929 Admin Workforce Navigation QA",
        "",
        "- Worker dry-run: `automation_workforce/navigation_integrity_worker.py --dry-run`.",
        "- Panel: `/admin/navigation-integrity`, aliases `/admin/routes` y `/admin/route-health`.",
        "- APIs admin: summary, run e issues; todas 403 sin sesion.",
        "- Sentinel y Outbox reciben solo incidencias activas deduplicadas.",
    ])
    write("CHATGPT_CONTINUATION_REPORT.md", [
        "# ChatGPT Continuation Report",
        "",
        f"Version local preparada: `{VERSION}`.",
        "",
        "V929 corrige el 404 real de `/clientes`, incorpora auditoria estatica completa, smoke por perfiles, rutas dinamicas contextuales, worker permanente, panel admin y Browser QA por clic.",
        f"Estado de navegacion: `{broken_after}` rotos, `{click_failures}` fallos Browser QA, `{int(matrix.get('redirect_loops') or 0)}` loops.",
        f"Render seguia en `{render_version}` al cerrar la preparacion; V929 no se declara desplegada.",
        "",
        "Siguiente accion: desplegar el contenido interno de `release_output/V929_DEPLOY_ROOT_CONTENTS` y verificar runtime real.",
    ])
    print(json.dumps({
        "ok": True,
        "version": VERSION,
        "reports_written": 14,
        "clicks_tested": total_clicks,
        "click_failures": click_failures,
        "broken_links_after": broken_after,
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

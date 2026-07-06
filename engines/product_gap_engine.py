"""V899 product gap engine.

Converts reference targets, static route knowledge and optional screenshots into
actionable issues/prompts. It is deliberately conservative: no fake data and no
claims of exact visual equivalence.
"""
from __future__ import annotations

from datetime import datetime
import hashlib
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


PRODUCT_GAP_ENGINE_VERSION = "V900_REFERENCE_IMAGES_IMPORT_FIRST_REAL_VISUAL_GAP_AUDIT_FINAL"
MADRID_TZ = ZoneInfo("Europe/Madrid")

TARGETS = [
    {"route": "/app", "category": "client", "device": "desktop", "priority": "high", "objective": "dashboard cliente premium con jerarquia, acciones y datos seguros"},
    {"route": "/app", "category": "mobile", "device": "mobile", "priority": "high", "objective": "app movil compacta sin overflow y con bottom nav clara"},
    {"route": "/admin/dashboard", "category": "admin", "device": "desktop", "priority": "high", "objective": "command center denso, claro y operativo"},
    {"route": "/picks", "category": "picks", "device": "desktop", "priority": "high", "objective": "picks como producto premium, sin cuota inventada"},
    {"route": "/live", "category": "live", "device": "desktop", "priority": "medium", "objective": "directos claros tipo marcador premium con estados reales"},
    {"route": "/calendar", "category": "calendar", "device": "desktop", "priority": "medium", "objective": "calendario denso, filtrable y honesto"},
    {"route": "/telegram", "category": "telegram", "device": "desktop", "priority": "medium", "objective": "Telegram premium sin filler ni envios inventados"},
    {"route": "/shark", "category": "shark", "device": "desktop", "priority": "medium", "objective": "SHARK como cerebro del producto y modo seguro si falta OpenAI"},
    {"route": "/membresias", "category": "memberships", "device": "desktop", "priority": "medium", "objective": "planes diferenciados con valor comercial real"},
    {"route": "/profile", "category": "profile", "device": "desktop", "priority": "medium", "objective": "perfil claro con plan, Telegram, seguridad y salida visible"},
    {"route": "/track-record", "category": "track-record", "device": "desktop", "priority": "medium", "objective": "historico honesto con resultados reales y sin ROI inventado"},
]

HEURISTICS = [
    "Pantalla demasiado vacia",
    "Cards pobres o sin jerarquia",
    "Falta de metricas visibles",
    "Botones genericos",
    "Texto excesivo",
    "Falta de iconos",
    "Falta de escudos/fallbacks",
    "Sidebar debil",
    "Bottom nav movil poco premium",
    "Admin poco command center",
    "Picks sin lectura premium",
    "Live/directo poco util",
    "Calendario con poca densidad",
    "SHARK poco integrado",
    "Membresias poco diferenciadas",
    "Tablas poco claras",
    "Falta de filtros",
    "Falta de KPIs",
    "Exceso de espacio negro vacio",
    "Diseno alejado de referencia",
]


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def _id(route: str, category: str, evidence: str) -> str:
    raw = f"{route}|{category}|{evidence}".encode("utf-8", errors="ignore")
    return "REFGAP-" + hashlib.sha1(raw).hexdigest()[:10].upper()


def _prompt(issue: dict[str, Any]) -> str:
    return (
        "Corrige esta diferencia visual/funcional en NeMeSiS SHARK PRO sin romper nada anterior.\n\n"
        f"ID:\n{issue['id']}\n\n"
        f"Pantalla:\n{issue.get('screen') or issue.get('route')}\n\n"
        f"Ruta:\n{issue.get('route')}\n\n"
        f"Referencia:\n{issue.get('reference') or 'Referencia pendiente o no disponible'}\n\n"
        f"Problema detectado:\n{issue.get('title')}\n\n"
        f"Por que se aleja de la referencia:\n{issue.get('evidence')}\n\n"
        f"Objetivo visual:\n{issue.get('objective')}\n\n"
        "Restricciones:\n"
        "* No inventar datos.\n"
        "* No tocar secretos.\n"
        "* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.\n"
        "* Mantener cliente/admin separados.\n"
        "* Mantener estados seguros si faltan datos reales.\n"
        "* Mantener responsive movil/PC.\n"
        "* No enviar Telegram real.\n"
        "* No hacer pagos reales.\n\n"
        "Que debes hacer:\n"
        f"{issue.get('recommendation')}\n\n"
        "Validaciones:\n"
        "* python -m py_compile app.py\n"
        "* python tools/run_continuous_sentinel_static.py\n"
        "* python tools/run_reference_visual_gap_scan.py --dry-run\n\n"
        "Entrega:\n"
        "* resumen;\n"
        "* archivos tocados;\n"
        "* capturas si existen;\n"
        "* checks;\n"
        "* limitaciones honestas.\n"
    )


def _references_for_category(manifest: dict[str, Any], category: str) -> list[dict[str, Any]]:
    if category == "mobile":
        direct_client = [item for item in manifest.get("items", []) if item.get("category") == "client"]
        secondary_mobile = [item for item in manifest.get("items", []) if "mobile" in (item.get("secondary_categories") or []) and item not in direct_client]
        return direct_client + secondary_mobile
    refs = []
    for item in manifest.get("items", []):
        secondary = item.get("secondary_categories") or []
        if item.get("category") == category or category in secondary:
            refs.append(item)
    return refs


def build_product_gap_report(
    root: str | Path,
    manifest: dict[str, Any],
    browser_result: dict[str, Any] | None = None,
    *,
    write: bool = True,
) -> dict[str, Any]:
    browser_result = browser_result or {}
    browser_available = bool(browser_result.get("browser_available"))
    captures = browser_result.get("screenshots") or []
    overflow_routes = {item.get("route") for item in captures if item.get("overflow_x")}
    gaps: list[dict[str, Any]] = []

    if not browser_available:
        gaps.append({
            "id": _id("browser", "browser_qa", "BROWSER_QA_UNAVAILABLE"),
            "title": "BROWSER_QA_UNAVAILABLE",
            "area": "reference_visual",
            "severity": "low",
            "status": "OPEN",
            "source": "reference_visual_gap_worker",
            "route": "browser",
            "screen": "Browser QA",
            "category": "browser_qa",
            "device": "desktop/mobile",
            "reference": "No aplica",
            "evidence": "Playwright no disponible o capturas no ejecutadas; no se puede comparar con precision visual real.",
            "objective": "Ejecutar browser QA real antes de afirmar cercania visual.",
            "recommendation": "Instalar Playwright o ejecutar la QA visual en entorno con navegador disponible.",
            "validation": ["python tools/run_browser_reference_qa.py --base-url http://127.0.0.1:5000"],
            "tags": ["reference_gap", "browser_qa"],
        })

    if not manifest.get("reference_count"):
        gaps.append({
            "id": _id("reference_images", "reference", "REFERENCE_IMAGES_MISSING"),
            "title": "REFERENCE_IMAGES_MISSING",
            "area": "reference_visual",
            "severity": "medium",
            "status": "OPEN",
            "source": "reference_visual_gap_worker",
            "route": "reference_images",
            "screen": "Banco de referencias",
            "category": "reference",
            "device": "all",
            "reference": "reference_images/",
            "evidence": "No hay imagenes reales de referencia; solo estructura/README.",
            "objective": "Anadir capturas/fotos de referencia por pantalla para comparar de verdad.",
            "recommendation": "Colocar referencias en reference_images/client, mobile, admin, picks, live, telegram, shark o memberships.",
            "validation": ["python tools/run_reference_visual_gap_scan.py --dry-run"],
            "tags": ["reference_gap", "reference_images"],
        })
    else:
        known_categories = sorted({item.get("category") for item in manifest.get("items", []) if item.get("category")})
        gaps.append({
            "id": _id("reference_images", "reference", "REFERENCE_IMAGES_IMPORTED"),
            "title": "REFERENCE_IMAGES_IMPORTED",
            "area": "reference_visual",
            "severity": "low",
            "status": "OPEN",
            "source": "reference_visual_gap_worker",
            "route": "reference_images",
            "screen": "Banco de referencias",
            "category": "reference",
            "device": "all",
            "reference": "reference_images/",
            "evidence": f"{manifest.get('reference_count', 0)} imagenes reales importadas; categorias: {', '.join(known_categories) or 'unknown'}.",
            "objective": "Usar referencias reales como base de gap visual.",
            "recommendation": "Comparar rutas objetivo contra referencias importadas y corregir solo diferencias visibles verificables.",
            "validation": ["python tools/run_reference_visual_gap_scan.py --dry-run"],
            "tags": ["reference_gap", "reference_images", "v900_imported"],
        })

    for target in TARGETS:
        refs = _references_for_category(manifest, target["category"])
        evidence_parts = []
        if not refs:
            evidence_parts.append("No hay referencia clasificada para esta categoria.")
        if target["route"] in overflow_routes:
            evidence_parts.append("Captura detecta overflow horizontal.")
        if not browser_available:
            evidence_parts.append("Pendiente de captura real; evaluacion limitada a heuristicas.")
        if not evidence_parts:
            evidence_parts.append("Requiere comparacion visual humana contra captura y referencia.")
        severity = "high" if target["priority"] == "high" and (not refs or target["route"] in overflow_routes) else "medium"
        if refs and not target["route"] in overflow_routes:
            severity = target["priority"]
        issue = {
            "id": _id(target["route"], target["category"], "|".join(evidence_parts)),
            "title": f"Gap visual de referencia en {target['route']}",
            "area": "reference_visual",
            "severity": severity,
            "status": "OPEN",
            "source": "reference_visual_gap_worker",
            "route": target["route"],
            "screen": target["route"],
            "category": target["category"],
            "device": target["device"],
            "reference": refs[0]["filename"] if refs else "Referencia pendiente",
            "evidence": " ".join(evidence_parts),
            "objective": target["objective"],
            "recommendation": f"Revisar {target['route']} contra la referencia de {target['category']} y corregir solo diferencias visibles reales.",
            "validation": ["python tools/run_reference_visual_gap_scan.py --dry-run", "python tools/run_continuous_sentinel_static.py"],
            "tags": ["reference_gap", target["category"], target["device"]],
            "heuristics": HEURISTICS,
        }
        issue["codex_prompt"] = _prompt(issue)
        issue["copy_text"] = f"[{issue['severity'].upper()}] {issue['title']} | Ruta: {issue['route']} | {issue['evidence']}"
        gaps.append(issue)

    for issue in gaps:
        issue.setdefault("codex_prompt", _prompt(issue))
        issue.setdefault("copy_text", f"[{issue.get('severity','low').upper()}] {issue.get('title')} | {issue.get('evidence')}")

    payload = {
        "version": PRODUCT_GAP_ENGINE_VERSION,
        "generated_at_madrid": _now(),
        "browser_available": browser_available,
        "reference_count": manifest.get("reference_count", 0),
        "targets_reviewed": TARGETS,
        "heuristics": HEURISTICS,
        "gaps": gaps,
        "issues": gaps,
        "critical_gaps": [gap for gap in gaps if gap.get("severity") == "critical"],
        "high_gaps": [gap for gap in gaps if gap.get("severity") == "high"],
        "codex_prompts": [gap["codex_prompt"] for gap in gaps],
        "score_honest": 100 - min(80, len([gap for gap in gaps if gap.get("severity") in {"critical", "high"}]) * 8 + len(gaps)),
        "safe_notes": [
            "No se declara equivalencia visual exacta.",
            "No se inventan datos deportivos.",
            "Las incidencias son tareas accionables para revisar pantalla por pantalla.",
        ],
    }
    if write:
        out = Path(root) / "data" / "runtime" / "autonomous_company_sentinel" / "reference_gap_report.json"
        out.parent.mkdir(parents=True, exist_ok=True)
        import json
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload

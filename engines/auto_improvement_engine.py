"""Safe self-improvement diagnostics for NeMeSiS SHARK PRO.

This module is intentionally read-only: no external calls, no code writes, no
deploys, no database mutation, and no secret exposure. It builds structured
diagnostics for admin panels, cron dry-runs, reports, and Codex prompts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import os
from typing import Any


SAFE_STATES = [
    "Sin datos reales",
    "Esperando proveedor",
    "Sin sincronizacion reciente",
    "Sin directos reales",
    "Sin picks activos",
    "Cuotas pendientes",
    "Resultado pendiente",
    "Sin pick real publicado",
    "Seleccion pendiente",
    "Pick en revision",
    "Archivado",
    "Liga baja relevancia",
    "No configurado",
    "Ultimo sync no disponible",
    "Sin errores registrados",
    "Accion pendiente",
    "Disponible en PRO",
    "Disponible en ELITE",
    "Desbloquea analisis avanzado",
    "Requiere sincronizacion real",
    "Proveedor sin datos ahora mismo",
]


FORBIDDEN_AUTOMATIC_ACTIONS = [
    "Modificar app.py o código de producto",
    "Hacer deploy automatico a Render",
    "Leer, mostrar o modificar secretos",
    "Borrar DB, usuarios, sesiones, membresias o pagos",
    "Enviar Telegram masivo o real sin aprobacion separada",
    "Inventar picks, cuotas, resultados, minutos o ROI",
    "Llamar APIs caras sin guard, presupuesto y accion aprobada",
]


@dataclass(frozen=True)
class ImprovementArea:
    area: str
    status: str
    score: int
    findings: list[str]
    risks: list[str]
    recommended_actions: list[str]
    safe_auto_actions: list[str]
    requires_admin_approval: list[str]
    next_focus: str


def _env_configured(*names: str) -> bool:
    return any(bool(str(os.getenv(name) or "").strip()) for name in names)


def _flag(runtime: dict[str, Any], key: str) -> bool:
    return bool(runtime.get(key))


def _status(score: int) -> str:
    if score >= 8:
        return "strong"
    if score >= 6:
        return "ok"
    return "needs_attention"


def _area(area: str, score: int, findings: list[str], risks: list[str], recommended: list[str], safe: list[str], approval: list[str], next_focus: str) -> dict[str, Any]:
    return asdict(ImprovementArea(
        area=area,
        status=_status(score),
        score=score,
        findings=findings,
        risks=risks,
        recommended_actions=recommended,
        safe_auto_actions=safe,
        requires_admin_approval=approval,
        next_focus=next_focus,
    ))


def build_auto_improvement_summary(version: str = "", runtime: dict[str, Any] | None = None, mode: str = "diagnostic", dry_run: bool = True) -> dict[str, Any]:
    """Return a safe operational diagnostic summary.

    Scores are structural and operational-readiness scores. They are not real
    revenue, betting, API-consumption, Telegram-delivery, or payment metrics.
    """
    runtime = dict(runtime or {})
    version = version or str(runtime.get("app_version") or runtime.get("version") or "unknown")
    render_known = bool(os.getenv("RENDER") or os.getenv("RENDER_SERVICE_NAME") or os.getenv("RENDER_EXTERNAL_HOSTNAME"))
    telegram_configured = _env_configured("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "TELEGRAM_CHANNEL_ID")
    api_configured = _env_configured("API_SPORTS_KEY", "APISPORTS_KEY", "API_FOOTBALL_KEY")
    odds_configured = _env_configured("THE_ODDS_API_KEY", "ODDS_API_KEY")
    openai_configured = _env_configured("OPENAI_API_KEY")
    payments_configured = _env_configured("STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "STRIPE_PRICE_PRO", "STRIPE_PRICE_ELITE")
    automation_secret = _env_configured("AUTOMATION_SECRET")

    areas = [
        _area(
            "Runtime & Render",
            8 if automation_secret and _flag(runtime, "has_v818_automation") else 6,
            [
                f"Version activa: {version}",
                "Master tick y health-check se mantienen como base protegida V818.",
                "La validacion Render real queda separada del diagnostico local.",
            ],
            [
                "El estado real de Render solo se confirma desde Render, no desde este panel local.",
                "Sin AUTOMATION_SECRET no se debe activar cron protegido.",
            ] if not automation_secret else ["Render real pendiente de validacion externa si no se ha probado deploy."],
            ["Validar runtime desplegado cuando exista URL Render real.", "Comparar /api/runtime-version local contra produccion."],
            ["Generar checklist runtime", "Refrescar diagnostico interno"],
            ["Lanzar deploy Render", "Cambiar variables de entorno"],
            "Validar Render real y cron con secret en entorno productivo.",
        ),
        _area(
            "Routes & Navigation",
            8,
            [
                "Rutas cliente/admin principales se mantienen centralizadas.",
                "V857 Company OS y V859 Product Board siguen como paneles de mando.",
                "Auto-Improvement OS se limita a diagnostico y recomendacion.",
            ],
            ["Las rutas nuevas deben mantenerse enlazadas en admin para no quedar huerfanas."],
            ["Auditar botones visibles con smoke de rutas despues de cada version."],
            ["Generar mapa de rutas", "Detectar enlaces administrativos clave"],
            ["Eliminar rutas legacy dudosas", "Cambiar navegacion principal de cliente"],
            "Mantener admin sin bottom nav cliente y sin acciones confusas.",
        ),
        _area(
            "Visual & UX",
            7,
            [
                "La direccion visual V858/V860 queda como referencia activa.",
                "El panel V861 no introduce una capa visual masiva.",
                "Los estados vacios deben seguir usando lenguaje premium y seguro.",
            ],
            ["Cualquier mejora visual real debe validarse con capturas, no solo por CSS."],
            ["Preparar una ronda con screenshots reales antes de declarar pixel-perfect."],
            ["Detectar mojibake comun", "Listar pantallas con estado vacio"],
            ["Redisenar masivamente pantallas sin QA visual"],
            "Proxima mejora visual solo con evidencias de pantalla real.",
        ),
        _area(
            "Data Reality",
            8 if api_configured or odds_configured else 6,
            [
                "La regla de no inventar datos se mantiene como politica central.",
                "API-SPORTS/API-Football y The Odds API se tratan como proveedores separados.",
                "Si falta dato real, se muestran estados seguros.",
            ],
            ["Sin claves reales no se puede afirmar consumo ni respuesta de proveedores.", "No deben existir llamadas por render."],
            ["Validar proveedor real en Render con guard de coste.", "Revisar cache/TTL antes de ampliar sincronizaciones."],
            ["Generar checklist de estados seguros", "Preparar prompt de auditoria de proveedor"],
            ["Sync masivo", "Recalcular picks", "Archivar picks reales"],
            "Probar API real con dry-run y presupuesto controlado.",
        ),
        _area(
            "Telegram",
            8 if telegram_configured else 6,
            [
                "V844 no filler y filtro premium se preservan.",
                "Auto-Improvement no envia Telegram real por defecto.",
                "Los descartes y candidatos deben seguir visibles para admin.",
            ],
            ["Sin envio real no se puede afirmar entrega al canal.", "Enviar test requiere aprobacion separada."],
            ["Validar ultimo envio real solo desde entorno configurado.", "Mantener dedupe antes de cualquier accion."],
            ["Preparar prompt de QA Telegram", "Revisar no filler en diagnostico"],
            ["Enviar Telegram test", "Enviar broadcast", "Cambiar token o destino"],
            "Validar canal real con accion manual aprobada.",
        ),
        _area(
            "SHARK IA",
            8 if openai_configured else 7,
            [
                "V845 SHARK mantiene fallback seguro sin OpenAI.",
                "El motor no debe prometer apuestas seguras ni inventar datos.",
                "Los prompts sugeridos por V861 son texto copiable, no ejecucion automatica.",
            ],
            ["Sin OPENAI_API_KEY real, la profundidad depende del fallback local."],
            ["Auditar respuestas con casos de partido sin cuota, sin minuto y sin pick real."],
            ["Detectar frases prohibidas", "Generar prompts Codex seguros"],
            ["Activar proveedor externo", "Guardar conversaciones sensibles"],
            "Reforzar evaluacion de no hallucination con casos reales.",
        ),
        _area(
            "Memberships & Payments",
            7 if payments_configured else 6,
            [
                "FREE/PRO/ELITE mantienen valor visual y bloqueos elegantes.",
                "Pagos reales no se simulan desde este sistema.",
                "Upgrade y beneficios deben permanecer honestos.",
            ],
            ["Sin prueba Stripe real no se puede afirmar cobro ni alta efectiva."],
            ["Validar Stripe en entorno controlado antes de venta real."],
            ["Generar checklist de planes", "Detectar mensajes de upgrade"],
            ["Modificar membresias reales", "Crear pagos", "Cambiar precios"],
            "Probar flujo de pago real en sandbox o Render configurado.",
        ),
        _area(
            "Company OS / Company Audit",
            9 if _flag(runtime, "has_v857_company_os") and _flag(runtime, "has_v859_company_audit_board") else 7,
            [
                "Workers V857 y Boards V859 quedan integrados con Auto-Improvement OS.",
                "La mejora continua observa y prioriza; no reescribe código.",
                "Las acciones sensibles quedan pendientes de aprobacion admin.",
            ],
            ["Si no se revisa periodicamente, el sistema puede convertirse en solo un panel informativo."],
            ["Usar los prompts generados para preparar siguientes versiones con foco."],
            ["Refrescar diagnostico", "Actualizar recomendaciones"],
            ["Ejecutar prompts Codex automaticamente", "Aplicar cambios de código"],
            "Convertir hallazgos recurrentes en tareas de producto priorizadas.",
        ),
        _area(
            "Release Cleanliness",
            8,
            [
                "build_clean_release y audit_release_zip siguen como cierre obligatorio.",
                "V861 no debe incluir DB local, logs, caches, ZIPs internos ni secretos.",
                "El endpoint cron solo diagnostica por defecto.",
            ],
            ["El ZIP final debe auditarse despues de reconstruirlo, no antes."],
            ["Ejecutar audit_release_zip sobre el ZIP final exacto."],
            ["Preparar checklist release", "Detectar patrones prohibidos"],
            ["Borrar legacy dudoso", "Mover archivos fuera de politica"],
            "Cerrar cada version con ZIP limpio y forbidden_count=0.",
        ),
    ]

    health_score = round(sum(item["score"] for item in areas) / max(1, len(areas)), 1)
    risks = [risk for item in areas for risk in item["risks"][:1]]
    recommended_actions = [action for item in areas for action in item["recommended_actions"][:1]]
    safe_auto_actions = [
        "Ejecutar diagnostico interno",
        "Generar reporte/checklist",
        "Preparar prompts Codex",
        "Detectar rutas o textos de riesgo",
        "Refrescar resumen sin llamadas externas",
    ]
    approval_required = [
        "Enviar Telegram test",
        "Lanzar sync grande",
        "Recalcular o archivar picks",
        "Modificar membresias o pagos",
        "Preparar release final",
        "Limpiar legacy dudoso",
    ]
    codex_prompts = [
        "Auditar Render real contra runtime local y documentar diferencias sin tocar secretos.",
        "Corregir visual movil con capturas reales y validar que no hay scroll horizontal.",
        "Revisar Telegram si no hay envios reales y mantener no filler/dedupe.",
        "Revisar picks sin cuotas y separar cuota pendiente, seleccion pendiente y pick en revision.",
        "Preparar hotfix de header invalid value si aparece en Render.",
        "Auditar pagos y membresias si Stripe sigue no configurado, sin inventar cobros.",
    ]

    return {
        "version": version,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "mode": mode if mode in {"diagnostic", "safe"} else "diagnostic",
        "dry_run": bool(dry_run),
        "global_status": "operational_diagnostic_safe",
        "health_score": health_score,
        "areas": areas,
        "findings": [finding for item in areas for finding in item["findings"][:1]],
        "risks": risks,
        "recommended_actions": recommended_actions,
        "safe_auto_actions": safe_auto_actions,
        "approval_required_actions": approval_required,
        "requires_admin_approval": approval_required,
        "forbidden_automatic_actions": FORBIDDEN_AUTOMATIC_ACTIONS,
        "codex_prompt_suggestions": codex_prompts,
        "next_focus": [
            "Validar Render real",
            "Revisar visual con capturas reales",
            "Auditar Telegram/API/pagos reales solo con entorno configurado",
            "Mantener ZIP limpio en cada release",
        ],
        "safe_states": SAFE_STATES,
        "blocked_by_real_render": not render_known,
        "blocked_by_real_api": not (api_configured or odds_configured),
        "blocked_by_real_payment": not payments_configured,
        "blocked_by_real_telegram": not telegram_configured,
        "safety_model": {
            "level_1_diagnostic_only": ["leer estado", "generar reportes", "crear checklist", "generar recomendaciones"],
            "level_2_safe_auto_heal": ["refrescar diagnosticos internos", "preparar tareas", "detectar duplicados", "recalcular reportes"],
            "level_3_requires_admin_approval": approval_required,
            "level_4_forbidden_automatic": FORBIDDEN_AUTOMATIC_ACTIONS,
        },
        "no_secrets": True,
        "no_code_writes": True,
        "no_deploy": True,
        "no_external_calls": True,
        "no_db_write_during_render": True,
        "no_fake_data": True,
    }


def run_auto_improvement_diagnostic(version: str = "", runtime: dict[str, Any] | None = None, mode: str = "diagnostic", dry_run: bool = True) -> dict[str, Any]:
    """Cron-safe entry point. It only returns diagnostics."""
    return {
        "ok": True,
        "executed": "diagnostic_only" if mode != "safe" else "safe_diagnostic_only",
        **build_auto_improvement_summary(version=version, runtime=runtime, mode=mode, dry_run=dry_run),
    }

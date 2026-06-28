"""V857 Company Operating System.

Internal product/QA operating layer. It describes specialized workers and safe
next steps without calling external providers, reading secrets, or inventing
business/data facts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


SAFE_STATES = [
    "Sin datos reales",
    "Esperando proveedor",
    "Sin sincronización reciente",
    "Sin directos reales",
    "Sin picks activos",
    "Cuotas pendientes",
    "Resultado pendiente",
    "Sin pick real publicado",
    "Selección pendiente",
    "Pick en revisión",
    "Archivado",
    "Liga baja relevancia",
    "No configurado",
    "Último sync no disponible",
    "Sin errores registrados",
    "Acción pendiente",
    "Disponible en PRO",
    "Disponible en ELITE",
    "Desbloquea análisis avanzado",
    "Requiere sincronización real",
    "Proveedor sin datos ahora mismo",
]


@dataclass(frozen=True)
class CompanyWorker:
    worker_name: str
    area: str
    status: str
    findings: list[str]
    recommended_actions: list[str]
    risk_level: str
    safe_next_step: str
    href: str


WORKER_BLUEPRINTS = [
    (
        "Product CEO Worker",
        "Producto y comercial",
        "/admin/company-os",
        ["Revisa si la app parece producto vendible o demo.", "Prioriza claridad, valor por plan y siguiente acción."],
        ["Mantener una pantalla fuerte por área: cliente, admin, SHARK, Telegram, picks y live."],
    ),
    (
        "Technical Director Worker",
        "Arquitectura y estabilidad",
        "/admin/system",
        ["Vigila rutas, dependencias y compatibilidad V818-V856.", "Evita cambios que llamen proveedores por render."],
        ["Verificar runtime, health-check y master tick antes de publicar."],
    ),
    (
        "Client Experience Worker",
        "Cliente móvil y PC",
        "/app",
        ["Comprueba navegación, pantallas, CTAs, estados vacíos y sensación premium.", "Marca pantallas que parezcan web antigua."],
        ["Revisar app center, partidos, live, picks, SHARK, Telegram, perfil y soporte."],
    ),
    (
        "Admin Command Center Worker",
        "Admin",
        "/admin/dashboard",
        ["Evita UI cliente dentro del admin.", "Ordena sistema, datos, Telegram, SHARK, usuarios, membresías, pagos y automatización."],
        ["Usar Company OS como índice de diagnóstico y decisiones."],
    ),
    (
        "Membership Value Worker",
        "Membresías",
        "/admin/memberships",
        ["Diferencia FREE, PRO, ELITE y ELITE+ sin inventar beneficios reales.", "Bloqueos elegantes y CTAs claros."],
        ["Mantener mensajes Disponible en PRO/ELITE y Desbloquea análisis avanzado."],
    ),
    (
        "SHARK Intelligence Worker",
        "SHARK IA",
        "/admin/shark-ai",
        ["Revisa contexto, fallback sin OpenAI y respuestas responsables.", "Bloquea lenguaje de apuesta segura."],
        ["Usar estados reales: cuotas pendientes, sin pick real, no hay datos suficientes."],
    ),
    (
        "Telegram Premium Worker",
        "Telegram",
        "/admin/telegram/command-center",
        ["Preserva V844: no filler, filtro premium y dedupe.", "No inventa envíos ni candidatos."],
        ["Mostrar descartes y motivos solo cuando existan datos internos."],
    ),
    (
        "Sports Data Worker",
        "API-SPORTS y live",
        "/admin/api-sports",
        ["Revisa proveedor, cache, live, resultados, fixtures y estados seguros.", "No gasta créditos por render."],
        ["Usar cache/guard y mostrar Esperando proveedor si falta dato."],
    ),
    (
        "Odds & Picks Worker",
        "The Odds API y picks",
        "/admin/picks",
        ["Distingue picks listos, en revisión, archivados, cuotas pendientes y selección pendiente.", "No inventa cuota, stake ni ROI."],
        ["Priorizar picks reales y degradar ligas de baja relevancia."],
    ),
    (
        "Crest & Identity Worker",
        "Escudos, logos y marca",
        "/admin/team-identity",
        ["Revisa fallback premium, logo NeMeSiS SHARK PRO y escudos ligeros.", "No inventa escudos oficiales."],
        ["Usar fallback si el proveedor no tiene logo real."],
    ),
    (
        "Routes & Buttons Worker",
        "Rutas y botones",
        "/admin/route-health",
        ["Detecta enlaces rotos, botones muertos, logout, soporte y navegación de vuelta.", "Verifica cliente y admin."],
        ["Mantener cada botón con ruta o acción real."],
    ),
    (
        "Spanish Copy Worker",
        "Español y copy",
        "/admin/company-os",
        ["Vigila mojibake, acentos, inglés innecesario y textos demo.", "Cliente debe sonar claro y comercial."],
        ["Usar estados premium seguros y frases cortas."],
    ),
    (
        "QA Visual Worker",
        "QA visual móvil/PC",
        "/admin/visual-qa",
        ["Revisa cards, layout, fondo SHARK, puntitos, mobile safe-area y PC dashboard.", "No declara pixel-perfect sin screenshots."],
        ["Comparar con referencias cuando existan capturas reales."],
    ),
    (
        "QA Data Reality Worker",
        "Datos reales",
        "/admin/data-center",
        ["Evita partidos, cuotas, minutos, ROI, usuarios, pagos o errores inventados.", "Exige estados seguros cuando falte proveedor."],
        ["Mostrar Sin datos reales o Proveedor sin datos ahora mismo."],
    ),
    (
        "Render ZIP Worker",
        "Render/GitHub/ZIP",
        "/admin/production-readiness",
        ["Revisa build limpio, audit_release_zip, forbidden_count y ausencia de secretos.", "No afirma Render real si no se probó."],
        ["Ejecutar build_clean_release y audit_release_zip antes de entregar."],
    ),
]


def _status_for(area: str, runtime: dict[str, Any] | None) -> str:
    runtime = runtime or {}
    if area == "API-SPORTS y live" and not (runtime.get("api_sports_configured") or runtime.get("api_football_configured")):
        return "Requiere configuración real"
    if area == "Telegram" and not runtime.get("telegram_configured"):
        return "No configurado"
    return "Operativo con revisión continua"


def _risk_for(status: str) -> str:
    if status in {"No configurado", "Requiere configuración real"}:
        return "medio"
    return "bajo"


def build_company_workers(runtime: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    workers: list[CompanyWorker] = []
    for name, area, href, findings, actions in WORKER_BLUEPRINTS:
        status = _status_for(area, runtime)
        workers.append(
            CompanyWorker(
                worker_name=name,
                area=area,
                status=status,
                findings=findings,
                recommended_actions=actions,
                risk_level=_risk_for(status),
                safe_next_step=actions[0],
                href=href,
            )
        )
    return [asdict(worker) for worker in workers]


def build_company_os_summary(version: str = "", runtime: dict[str, Any] | None = None) -> dict[str, Any]:
    workers = build_company_workers(runtime)
    medium_or_high = [worker for worker in workers if worker["risk_level"] != "bajo"]
    return {
        "version": version,
        "global_status": "operativo_con_revision" if not medium_or_high else "operativo_con_pendientes",
        "safe_mode": True,
        "secrets_exposed": False,
        "external_calls": False,
        "data_invention_allowed": False,
        "safe_states": SAFE_STATES,
        "workers": workers,
        "areas": sorted({worker["area"] for worker in workers}),
        "findings": [finding for worker in workers for finding in worker["findings"]],
        "recommendations": [worker["safe_next_step"] for worker in workers],
        "protected_foundations": [
            "V818 master tick",
            "V844 Telegram premium/no filler",
            "V845 SHARK IA",
            "V847 API-SPORTS guard",
            "V850 live/escudos",
            "V853 admin command center",
            "V856 second pass",
        ],
    }

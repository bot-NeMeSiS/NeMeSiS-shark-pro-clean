"""V857 Company Operating System.

Internal product/QA responsibility catalog. It describes roles and safe
next steps without calling external providers, reading secrets, or inventing
business/data facts.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import PurePosixPath
import re
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
    configuration_status: str = ""
    execution_state: str = "UNVERIFIED"


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
        ["Diferencia FREE, PRO y ELITE según los permisos reales; Admin conserva su espacio de administración.", "Bloqueos elegantes y CTAs claros."],
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


def _configuration_status_for(area: str, runtime: dict[str, Any] | None) -> str:
    runtime = runtime or {}
    if area == "API-SPORTS y live" and not (runtime.get("api_sports_configured") or runtime.get("api_football_configured")):
        return "Requiere configuración real"
    if area == "Telegram" and not runtime.get("telegram_configured"):
        return "No configurado"
    return ""


def _risk_for(status: str) -> str:
    if status in {"No configurado", "Requiere configuración real"}:
        return "medio"
    return "bajo"


def _review_evidence(records):
    """Keep only bounded source identity, never source contents or raw errors."""
    result = []
    for item in records[:16] if isinstance(records, list) else []:
        if not isinstance(item, dict):
            continue
        path, digest = item.get("path"), item.get("sha256")
        if (not isinstance(path, str) or not re.fullmatch(r"[A-Za-z0-9_./-]{1,180}", path)
                or PurePosixPath(path).is_absolute() or ".." in PurePosixPath(path).parts):
            continue
        state = item.get("state")
        result.append({"path": path,
                       "sha256": digest if isinstance(digest, str) and re.fullmatch(r"[0-9a-f]{64}", digest) else "",
                       "state": state if isinstance(state, str) and re.fullmatch(r"[A-Z_]{1,32}", state) else "UNAVAILABLE"})
    return result


def build_company_workers(runtime: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    workers: list[CompanyWorker] = []
    for name, area, href, findings, actions in WORKER_BLUEPRINTS:
        configuration_status = _configuration_status_for(area, runtime)
        workers.append(
            CompanyWorker(
                worker_name=name,
                area=area,
                # These blueprints carry responsibilities, not execution receipts.
                status="Sin ejecución acreditada",
                findings=findings,
                recommended_actions=actions,
                risk_level=_risk_for(configuration_status),
                safe_next_step=actions[0],
                href=href,
                configuration_status=configuration_status,
            )
        )
    return [asdict(worker) for worker in workers]


def build_company_os_summary(version: str = "", runtime: dict[str, Any] | None = None, *, project_root=None, storage_root=None, now=None) -> dict[str, Any]:
    workers = build_company_workers(runtime)
    from engines.game_ui_review_lab import build_game_ui_lab
    from engines.company_workforce_receipts_engine import master_cron_receipt
    import os
    db_path = (runtime or {}).get("db_path") or os.getenv("DB_PATH", "")
    # This is a bounded receipt read only. Visiting Company OS never runs the
    # review cycle, advances its clock or writes a result. Keep the import lazy
    # because the review engine also consumes this responsibility catalog.
    try:
        from engines.product_review_system_engine import load_native_workforce_receipt
        review = load_native_workforce_receipt(project_root, storage_root=storage_root, now=now)
    except Exception:
        review = {"state": "UNAVAILABLE", "receipt": {}, "results": []}
    receipt = review.get("receipt") if isinstance(review.get("receipt"), dict) else {}
    records = review.get("results") if isinstance(review.get("results"), list) else []
    recent = review.get("state") == "RECENT" and receipt.get("contract") == "NEMESIS-NATIVE-WORKFORCE-REVIEW-V1"
    by_worker = {row.get("worker_name"): row for row in records if isinstance(row, dict) and isinstance(row.get("worker_name"), str)}
    labels = {"PASS": "Comprobación estática conforme", "FAIL": "Hallazgo estático que revisar", "UNKNOWN": "Revisión estática con evidencia pendiente"}
    reviewed = 0
    for worker in workers:
        recorded = by_worker.get(worker["worker_name"], {})
        if recent and recorded.get("state") in labels and recorded.get("executed") is True:
            reviewed += 1
            worker["status"] = labels[recorded["state"]]
            worker["execution_state"] = "STATIC_PARTIAL"
            findings = recorded.get("findings") if isinstance(recorded.get("findings"), list) else []
            proposal = recorded.get("proposal")
            if not isinstance(proposal, str):
                proposal = next((item.get("proposal") for item in findings if isinstance(item, dict) and isinstance(item.get("proposal"), str)), "")
            worker["static_review"] = {
                "state": recorded["state"],
                "finished_at_madrid": str(receipt.get("finished_at_madrid") or "")[:80],
                "limitation": str(recorded.get("limitation") or "Revisión estática; funcionamiento real sin certificar.")[:360],
                "check_ids": [str(x)[:100] for x in (recorded.get("check_ids") or [])[:16]] if isinstance(recorded.get("check_ids"), list) else [],
                "proposal": proposal[:420],
                "evidence": _review_evidence(recorded.get("evidence")),
                "checks": [{"state": check["state"], "detail": check["result"][:360]}
                           for check in (recorded.get("checks") if isinstance(recorded.get("checks"), list) else [])[:16]
                           if isinstance(check, dict) and isinstance(check.get("state"), str) and check["state"] in labels and isinstance(check.get("result"), str)],
            }
    game_ui_lab = build_game_ui_lab(review=review)
    return {
        "version": version,
        "global_status": "responsabilidades_configuradas",
        "execution_state": "STATIC_PARTIAL" if reviewed or game_ui_lab.get("reviewed_count") else "UNVERIFIED",
        "configuration_attention_count": sum(bool(worker["configuration_status"]) for worker in workers),
        "safe_mode": True,
        "secrets_exposed": False,
        "external_calls": False,
        "data_invention_allowed": False,
        "safe_states": SAFE_STATES,
        "workers": workers,
        "game_ui_lab": game_ui_lab,
        "native_workforce_review": {
            "state": review.get("state") if review.get("state") in {"RECENT", "STALE", "NOT_RUN", "UNAVAILABLE", "CLOCK_UNVERIFIED"} else "UNAVAILABLE",
            "finished_at_madrid": str(receipt.get("finished_at_madrid") or "")[:80],
            "run_id": str(receipt.get("run_id") or "")[:100],
            "reviewed_core_count": reviewed,
            "reviewed_game_count": game_ui_lab.get("reviewed_count", 0),
            "scope": "STATIC_PARTIAL",
        },
        "workforce_receipt": master_cron_receipt(db_path),
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

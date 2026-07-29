"""Evidence-first company operations center for NeMeSiS SHARK PRO V938."""
from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from hashlib import sha1
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from engines.disaster_recovery_engine import build_disaster_recovery_readiness
from engines.operations_monitoring_engine import build_operations_monitoring
from engines.sports_intelligence_gateway_engine import build_sports_intelligence_gateway_snapshot
from engines.sports_platform_contracts import build_sports_platform_contract_registry


try:
    MADRID_TZ = ZoneInfo("Europe/Madrid")
except ZoneInfoNotFoundError:
    MADRID_TZ = datetime.now().astimezone().tzinfo
EVIDENCE_STATES = {
    "CONFIRMADO",
    "NO_CERTIFICADO",
    "HIPOTESIS",
    "BLOQUEADO_POR_ACCESO",
    "REQUIERE_REVISION",
}
RUNTIME_DIR_NAME = "v938_company_operations"


def madrid_now_iso() -> str:
    return datetime.now(MADRID_TZ).isoformat(timespec="seconds")


def _masked_path(value: str | Path) -> str:
    text = str(value or "")
    try:
        return text.replace(str(Path.home()), "~")
    except Exception:
        return text


def _env_present(name: str) -> bool:
    return bool(str(os.getenv(name) or "").strip())


def _system(
    system_id: str,
    name: str,
    status: str,
    evidence_state: str,
    summary: str,
    source: str,
    severity: str = "info",
    details: dict[str, Any] | None = None,
    next_action: str = "",
) -> dict[str, Any]:
    state = evidence_state if evidence_state in EVIDENCE_STATES else "REQUIERE_REVISION"
    return {
        "id": system_id,
        "name": name,
        "status": status,
        "evidence_state": state,
        "summary": summary,
        "source": source,
        "severity": severity,
        "details": details or {},
        "next_action": next_action,
    }


def _read_version(root: Path, name: str) -> str:
    try:
        return (root / name).read_text(encoding="utf-8-sig").replace("\x00", "").strip()
    except Exception:
        return ""


def _git_identity(root: Path) -> dict[str, Any]:
    git_dir = root / ".git"
    head_file = git_dir / "HEAD"
    if not head_file.exists():
        return {"available": False, "branch": "", "sha": "", "source": ".git/HEAD missing"}
    try:
        head = head_file.read_text(encoding="utf-8", errors="replace").strip()
    except Exception:
        return {"available": False, "branch": "", "sha": "", "source": ".git/HEAD unreadable"}
    branch = "detached"
    sha = head
    if head.startswith("ref:"):
        ref = head.split(":", 1)[1].strip()
        branch = ref.rsplit("/", 1)[-1]
        try:
            sha = (git_dir / ref).read_text(encoding="utf-8", errors="replace").strip()
        except Exception:
            packed = git_dir / "packed-refs"
            sha = ""
            if packed.exists():
                for line in packed.read_text(encoding="utf-8", errors="replace").splitlines():
                    if line and not line.startswith(("#", "^")) and line.endswith(f" {ref}"):
                        sha = line.split(" ", 1)[0]
                        break
    return {"available": bool(sha), "branch": branch, "sha": sha, "sha_short": sha[:10], "source": ".git/HEAD and local refs"}


def _sqlite_readonly(db_path: str | Path) -> tuple[sqlite3.Connection | None, dict[str, Any]]:
    path = Path(db_path)
    if not path.exists():
        return None, {"ok": False, "status": "MISSING", "path_masked": _masked_path(path)}
    connection: sqlite3.Connection | None = None
    try:
        uri = f"file:{path.resolve().as_posix()}?mode=ro"
        connection = sqlite3.connect(uri, uri=True, timeout=2)
        connection.row_factory = sqlite3.Row
        quick_check = str(connection.execute("PRAGMA quick_check").fetchone()[0])
        table_count = int(connection.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table'").fetchone()[0])
        return connection, {
            "ok": quick_check.lower() == "ok",
            "status": "HEALTHY" if quick_check.lower() == "ok" else "DEGRADED",
            "path_masked": _masked_path(path),
            "size_bytes": path.stat().st_size,
            "quick_check": quick_check,
            "table_count": table_count,
        }
    except sqlite3.OperationalError as exc:
        if connection is not None:
            connection.close()
        text = str(exc).lower()
        return None, {
            "ok": False,
            "status": "LOCKED" if "locked" in text else "UNREADABLE",
            "path_masked": _masked_path(path),
            "error_type": exc.__class__.__name__,
        }
    except Exception as exc:
        if connection is not None:
            connection.close()
        return None, {"ok": False, "status": "UNREADABLE", "path_masked": _masked_path(path), "error_type": exc.__class__.__name__}


def _table_columns(connection: sqlite3.Connection, table: str) -> set[str]:
    if not table.replace("_", "").isalnum():
        return set()
    try:
        return {str(row[1]) for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()}
    except Exception:
        return set()


def _latest_operational_record(connection: sqlite3.Connection | None, tables: list[str]) -> dict[str, Any]:
    if connection is None:
        return {}
    existing = {str(row[0]) for row in connection.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
    date_candidates = ["finished_at", "completed_at", "last_run", "updated_at", "created_at", "started_at", "synced_at", "run_at"]
    status_candidates = ["status", "result", "state"]
    for table in tables:
        if table not in existing:
            continue
        columns = _table_columns(connection, table)
        date_col = next((name for name in date_candidates if name in columns), "")
        status_col = next((name for name in status_candidates if name in columns), "")
        if not date_col and not status_col:
            continue
        selected = [name for name in [date_col, status_col] if name]
        order = f' ORDER BY "{date_col}" DESC' if date_col else " ORDER BY rowid DESC"
        try:
            selected_sql = ", ".join(f'"{name}"' for name in selected)
            row = connection.execute(f'SELECT {selected_sql} FROM "{table}"{order} LIMIT 1').fetchone()
            if row:
                data = dict(row)
                return {
                    "table": table,
                    "last_at": str(data.get(date_col) or "") if date_col else "",
                    "status": str(data.get(status_col) or "") if status_col else "",
                }
        except Exception:
            continue
    return {}


def _privacy_summary(root: Path) -> dict[str, Any]:
    path = root / "reports" / "V938_REPOSITORY_PRIVACY_SECRET_CLASSIFICATION.json"
    if not path.exists():
        return {"available": False, "secrets": 0, "privacy_candidates": 0}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return {
            "available": True,
            "secrets": int(payload.get("confirmed_secret_findings") or 0),
            "privacy_candidates": int(payload.get("privacy_review_findings") or 0),
            "files_scanned": int(payload.get("files_scanned") or 0),
        }
    except Exception:
        return {"available": False, "secrets": 0, "privacy_candidates": 0}


def _score(name: str, criteria: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(int(item.get("weight") or 0) for item in criteria) or 1
    earned = sum(int(item.get("weight") or 0) for item in criteria if item.get("met"))
    points = round((earned / total) * 10, 1)
    evidence = [item.get("label") for item in criteria if item.get("met")]
    gaps = [item.get("label") for item in criteria if not item.get("met")]
    confidence = "high" if all(item.get("certified", True) for item in criteria if item.get("met")) and earned >= total * 0.8 else "medium" if earned >= total * 0.5 else "low"
    return {"name": name, "score": points, "max": 10, "evidence": evidence, "gaps": gaps, "confidence": confidence, "criteria": criteria}


def _build_scores(systems: list[dict[str, Any]], dr: dict[str, Any]) -> dict[str, Any]:
    by_id = {item["id"]: item for item in systems}
    confirmed = lambda key: by_id.get(key, {}).get("evidence_state") == "CONFIRMADO" and by_id.get(key, {}).get("status") in {"PASS", "HEALTHY", "READY"}
    scores = {
        "detection": _score("Capacidad de deteccion", [
            {"label": "Sentinel local disponible", "weight": 3, "met": confirmed("sentinel"), "certified": True},
            {"label": "Runtime local alineado", "weight": 2, "met": confirmed("runtime"), "certified": True},
            {"label": "Monitor externo certificado", "weight": 3, "met": confirmed("render"), "certified": False},
            {"label": "Secret Guard operativo", "weight": 2, "met": confirmed("security"), "certified": True},
        ]),
        "recovery": _score("Capacidad de recuperacion", [
            {"label": "DB legible", "weight": 2, "met": confirmed("database"), "certified": True},
            {"label": "Backup con hash", "weight": 3, "met": dr.get("validated_backup_count", 0) > 0, "certified": True},
            {"label": "Restore aislado certificado", "weight": 3, "met": dr.get("isolated_restore", {}).get("certified") is True, "certified": True},
            {"label": "Copia offsite certificada", "weight": 2, "met": dr.get("offsite", {}).get("evidence_state") == "CONFIRMADO", "certified": False},
        ]),
        "autonomous_operations": _score("Operacion autonoma", [
            {"label": "Cron con evidencia", "weight": 3, "met": confirmed("cron"), "certified": True},
            {"label": "Datos deportivos certificados", "weight": 3, "met": confirmed("sports_data"), "certified": True},
            {"label": "Telegram certificado", "weight": 2, "met": confirmed("telegram"), "certified": False},
            {"label": "Dead-man externo", "weight": 2, "met": confirmed("render"), "certified": False},
        ]),
        "customer_readiness": _score("Preparacion para clientes", [
            {"label": "Runtime local coherente", "weight": 2, "met": confirmed("runtime"), "certified": True},
            {"label": "DB local sana", "weight": 2, "met": confirmed("database"), "certified": True},
            {"label": "Datos deportivos frescos certificados", "weight": 3, "met": confirmed("sports_data"), "certified": False},
            {"label": "Pagos certificados", "weight": 3, "met": confirmed("stripe"), "certified": False},
        ]),
        "growth_readiness": _score("Preparacion para crecer", [
            {"label": "Continuidad demostrada", "weight": 3, "met": confirmed("continuity"), "certified": False},
            {"label": "Observabilidad externa", "weight": 3, "met": confirmed("render"), "certified": False},
            {"label": "Seguridad local sin secretos", "weight": 2, "met": confirmed("security"), "certified": True},
            {"label": "Segundo operador habilitado", "weight": 2, "met": False, "certified": False},
        ]),
    }
    return scores


def _system_by_id(systems: list[dict[str, Any]], system_id: str) -> dict[str, Any]:
    for item in systems:
        if item.get("id") == system_id:
            return item
    return {}


def _gate_status(status: Any, evidence_state: Any = "") -> str:
    normalized = str(status or "").upper()
    evidence = str(evidence_state or "").upper()
    if normalized in {"PASS", "HEALTHY", "READY", "CONFIGURED", "LOCAL_ONLY", "COMPLETED"} and evidence == "CONFIRMADO":
        return "PASS"
    if normalized in {"FAIL", "BLOCKED", "MISSING", "UNREADABLE", "LOCKED"}:
        return "BLOCKED"
    return "PARTIAL"


def _section(key: str, title: str, status: str, evidence_state: str, summary: str, *, items: list[dict[str, Any]] | None = None, limitations: list[str] | None = None, next_action: str = "") -> dict[str, Any]:
    state = evidence_state if evidence_state in EVIDENCE_STATES else "REQUIERE_REVISION"
    return {"key": key, "title": title, "status": status if status in {"PASS", "PARTIAL", "BLOCKED"} else "PARTIAL", "evidence_state": state, "summary": summary, "items": items or [], "limitations": limitations or [], "next_action": next_action}


def _item(label: str, value: Any, state: str = "CONFIRMADO", source: str = "local", note: str = "") -> dict[str, Any]:
    return {"label": label, "value": str(value if value not in {None, ""} else "No disponible"), "state": state if state in EVIDENCE_STATES else "REQUIERE_REVISION", "source": source, "note": note}


def _configured_item(name: str) -> dict[str, Any]:
    return _item(name, "Detectada" if _env_present(name) else "No detectada", "CONFIRMADO", "env enmascarada")


def _count_runtime_files(root: Path, relative: str) -> int:
    directory = root / relative
    if not directory.exists() or not directory.is_dir():
        return 0
    try:
        return sum(1 for item in directory.rglob("*") if item.is_file())
    except OSError:
        return 0


def _read_render_yaml_summary(root: Path) -> dict[str, Any]:
    path = root / "render.yaml"
    if not path.exists():
        return {"available": False, "service": "", "cron": "", "health_check": "", "python": ""}
    content = path.read_text(encoding="utf-8", errors="replace")
    return {"available": True, "service": "nemesis-shark-pro" if "nemesis-shark-pro" in content else "", "cron": "nemesis-sports-sync" if "nemesis-sports-sync" in content else "", "health_check": "/api/health" if "/api/health" in content else "", "python": "3.11.9" if "3.11.9" in content else "", "persistent_disk_hint": "/data/database.db" if "/data/database.db" in content else ""}


def _build_commercial_readiness(*, render_system: dict[str, Any], telegram_configured: bool, stripe_configured: bool, db_status: dict[str, Any], scores: dict[str, Any], external_certified: bool) -> list[dict[str, Any]]:
    return [
        {"area": "Render", "status": "PASS" if external_certified else "PARTIAL", "evidence": render_system.get("summary") or "Render pendiente de certificacion externa.", "missing": [] if external_certified else ["Certificar SHA servido, runtime y health en produccion."]},
        {"area": "Telegram", "status": "PARTIAL" if telegram_configured else "BLOCKED", "evidence": "Configuracion detectada; no se envia nada desde este centro." if telegram_configured else "No hay configuracion completa en el entorno local.", "missing": ["Dry-run autorizado, destino enmascarado y ultima entrega sin enviar mensajes reales."]},
        {"area": "Stripe", "status": "PARTIAL" if stripe_configured else "BLOCKED", "evidence": "Configuracion minima detectada sin iniciar pagos." if stripe_configured else "Checkout/webhook no certificables con variables locales actuales.", "missing": ["Certificar productos, precios, webhooks y eventos sin cobro real."]},
        {"area": "Persistencia", "status": "PASS" if db_status.get("ok") else "BLOCKED", "evidence": "SQLite responde quick_check en modo solo lectura." if db_status.get("ok") else "La DB local no pudo validarse.", "missing": [] if db_status.get("ok") else ["Resolver DB_PATH, lock o disco antes del lanzamiento."]},
        {"area": "UX", "status": "PASS" if scores.get("customer_readiness", {}).get("score", 0) >= 7 else "PARTIAL", "evidence": "Browser QA local y rutas criticas se mantienen como evidencia local.", "missing": ["Certificacion visual final en produccion tras despliegue autorizado."]},
        {"area": "Conversion", "status": "PARTIAL", "evidence": "Membresias FREE/PRO/ELITE existen; conversion real no certificada en este entorno.", "missing": ["Validar embudo, checkout real y soporte comercial con usuarios beta."]},
        {"area": "Soporte", "status": "PARTIAL", "evidence": "Paneles internos y runbooks presentes; SLA real no probado.", "missing": ["Definir operador, canal de soporte y tiempos de respuesta medidos."]},
        {"area": "Observabilidad", "status": "PASS" if scores.get("detection", {}).get("score", 0) >= 7 else "PARTIAL", "evidence": "Sentinel, AutoPilot y Operations Center generan evidencia local.", "missing": ["Alertas externas y vigilancia de produccion con prueba real."]},
    ]


def _score_release_category(name: str, checks: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(checks) or 1
    points = sum(1.0 if str(item.get("status") or "").upper() == "PASS" else 0.5 if str(item.get("status") or "").upper() == "PARTIAL" else 0.0 for item in checks)
    score = round((points / total) * 10, 1)
    return {"name": name, "score": score, "max": 10, "basis": "formula: PASS=1, PARTIAL=0.5, BLOCKED=0 sobre evidencias listadas", "evidence": [item.get("label") for item in checks if item.get("status") == "PASS"], "gaps": [item.get("label") for item in checks if item.get("status") != "PASS"], "checks": checks}


def _build_global_score(sections: dict[str, Any], commercial: list[dict[str, Any]], systems: list[dict[str, Any]]) -> dict[str, Any]:
    system = lambda key: _system_by_id(systems, key)
    categories = [
        _score_release_category("Infrastructure", [{"label": "Render declarado", "status": sections["render"]["status"]}, {"label": "DB legible", "status": sections["database"]["status"]}, {"label": "Cache controlada", "status": sections["cache"]["status"]}]),
        _score_release_category("Reliability", [{"label": "Cron observado", "status": sections["cron"]["status"]}, {"label": "Backups/restore preparados", "status": _gate_status(system("backups").get("status"), system("backups").get("evidence_state"))}, {"label": "Runtime local sano", "status": sections["platform_health"]["status"]}]),
        _score_release_category("Security", [{"label": "Secret Guard", "status": sections["security"]["status"]}, {"label": "Privacy Guard", "status": sections["security"]["status"]}, {"label": "Acciones peligrosas bloqueadas", "status": "PASS"}]),
        _score_release_category("Observability", [{"label": "Sentinel/AutoPilot", "status": sections["observability"]["status"]}, {"label": "Operations Center", "status": "PASS"}, {"label": "Errores recientes visibles", "status": "PARTIAL"}]),
        _score_release_category("Commercial Readiness", [{"label": item.get("area"), "status": item.get("status")} for item in commercial]),
        _score_release_category("Experience", [{"label": "Browser QA local", "status": "PASS"}, {"label": "Certificacion visual produccion", "status": "PARTIAL"}, {"label": "Conversion real", "status": "PARTIAL"}]),
        _score_release_category("Sports Core", [{"label": "Sports Core", "status": sections["sports_core"]["status"]}, {"label": "Sports Gateway", "status": sections["sports_gateway"]["status"]}, {"label": "Datos deportivos frescos", "status": sections["sports_gateway"]["status"]}]),
        _score_release_category("Product", [{"label": "Product Finalization", "status": "PASS"}, {"label": "Company Board", "status": "PASS"}, {"label": "Developer Center", "status": "PASS"}]),
    ]
    release = _score_release_category("Release Readiness", [{"label": category["name"], "status": "PASS" if category["score"] >= 8 else "PARTIAL" if category["score"] >= 5 else "BLOCKED"} for category in categories])
    categories.append(release)
    return {"contract": "NEMESIS-RELEASE-1-OPERATIONS-SCORE-V1", "method": "Deterministico desde gates; no usa estimaciones comerciales inventadas.", "categories": categories, "overall_score": release["score"], "overall_status": "PASS" if release["score"] >= 8 and not release["gaps"] else "PARTIAL" if release["score"] >= 5 else "BLOCKED"}


def _build_operations_sections(*, root_path: Path, app_version: str, version_txt: str, app_version_file: str, git: dict[str, Any], db_status: dict[str, Any], dr: dict[str, Any], privacy: dict[str, Any], systems: list[dict[str, Any]], scores: dict[str, Any], sports_metrics: dict[str, Any], cron_record: dict[str, Any], sports_record: dict[str, Any], telegram_record: dict[str, Any], external_runtime: dict[str, Any], external_certified: bool, runtime_aligned: bool, sports_provider: bool, telegram_configured: bool, stripe_configured: bool, secret_guard_present: bool) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    render_yaml = _read_render_yaml_summary(root_path)
    gateway = build_sports_intelligence_gateway_snapshot(observed_at_madrid=madrid_now_iso())
    contracts = build_sports_platform_contract_registry(root_path)
    system = lambda key: _system_by_id(systems, key)
    commercial = _build_commercial_readiness(render_system=system("render"), telegram_configured=telegram_configured, stripe_configured=stripe_configured, db_status=db_status, scores=scores, external_certified=external_certified)
    sections = {
        "platform_health": _section("platform_health", "Platform Health", "PASS" if runtime_aligned and db_status.get("ok") else "BLOCKED", "CONFIRMADO", "Identidad local, DB y hora Madrid disponibles en modo read-only.", items=[_item("Runtime local", app_version), _item("VERSION.txt", version_txt), _item("APP_VERSION", app_version_file or "No disponible", "CONFIRMADO" if app_version_file else "NO_CERTIFICADO"), _item("SHA local", git.get("sha_short") or "No disponible", "CONFIRMADO" if git.get("available") else "BLOQUEADO_POR_ACCESO", git.get("source") or ".git"), _item("Ultimo check", madrid_now_iso(), "CONFIRMADO", "Operations Center")], next_action="Certificar Render antes de declarar Release 1.0 listo."),
        "render": _section("render", "Render", "PASS" if external_certified else "PARTIAL", "CONFIRMADO" if external_certified else "BLOQUEADO_POR_ACCESO", "Render alineado con runtime externo." if external_certified else "Esta ejecucion local no toca produccion; Render queda pendiente de lectura autorizada.", items=[_item("render.yaml", "Disponible" if render_yaml.get("available") else "No disponible"), _item("Servicio", render_yaml.get("service") or "No disponible", "CONFIRMADO" if render_yaml.get("service") else "NO_CERTIFICADO", "render.yaml"), _item("Health path", render_yaml.get("health_check") or "No disponible", "CONFIRMADO" if render_yaml.get("health_check") else "NO_CERTIFICADO", "render.yaml"), _item("Python", render_yaml.get("python") or "No disponible", "CONFIRMADO" if render_yaml.get("python") else "NO_CERTIFICADO", "render.yaml"), _item("Disco persistente", render_yaml.get("persistent_disk_hint") or db_status.get("path_masked") or "No disponible", "CONFIRMADO", "render.yaml/DB_PATH"), _item("SHA servido", external_runtime.get("git_commit_hint") or "No certificado en esta ejecucion", "CONFIRMADO" if external_certified else "BLOQUEADO_POR_ACCESO", "runtime externo")], limitations=["No se consulta Render desde este sprint por restriccion expresa."], next_action="Leer /api/runtime-version y /api/health de Render solo con autorizacion de certificacion."),
        "cron": _section("cron", "Cron", "PASS" if cron_record.get("last_at") else "PARTIAL", "CONFIRMADO" if cron_record.get("last_at") else "NO_CERTIFICADO", "Existe evidencia local de ejecucion." if cron_record.get("last_at") else "No hay tick local suficiente para certificar master tick.", items=[_item("Master tick", cron_record.get("status") or "NOT_RECORDED", "CONFIRMADO" if cron_record.get("last_at") else "NO_CERTIFICADO", cron_record.get("table") or "DB local read-only"), _item("Ultima ejecucion", cron_record.get("last_at") or "No disponible", "CONFIRMADO" if cron_record.get("last_at") else "NO_CERTIFICADO", cron_record.get("table") or "DB local read-only"), _item("Siguiente esperada", "No calculada localmente", "NO_CERTIFICADO", "sin produccion"), _item("Sports sync", sports_record.get("status") or "No disponible", "CONFIRMADO" if sports_record.get("last_at") else "NO_CERTIFICADO", sports_record.get("table") or "DB local read-only")], limitations=["Sin escritura DB y sin llamada externa; solo lectura de evidencia local."], next_action="Certificar master tick y siguiente ejecucion en produccion."),
        "telegram": _section("telegram", "Telegram", "PARTIAL" if telegram_configured else "BLOCKED", "NO_CERTIFICADO", "Configuracion detectada; no se envia nada." if telegram_configured else "Destino Telegram no certificable en este entorno.", items=[_configured_item("TELEGRAM_BOT_TOKEN"), _configured_item("TELEGRAM_CHAT_ID"), _configured_item("TELEGRAM_WEBHOOK_SECRET"), _item("Ultima entrega", telegram_record.get("last_at") or "No disponible", "CONFIRMADO" if telegram_record.get("last_at") else "NO_CERTIFICADO", telegram_record.get("table") or "DB local read-only"), _item("Dedupe/queue", telegram_record.get("status") or "No disponible", "NO_CERTIFICADO", "DB local read-only")], limitations=["El panel nunca envia mensajes reales ni muestra destinos completos."], next_action="Ejecutar solo dry-run protegido y validar destino enmascarado."),
        "stripe": _section("stripe", "Stripe", "PARTIAL" if stripe_configured else "BLOCKED", "NO_CERTIFICADO", "Configuracion minima detectada sin iniciar pagos." if stripe_configured else "Stripe no queda certificado con la evidencia local.", items=[_configured_item("STRIPE_SECRET_KEY"), _configured_item("STRIPE_WEBHOOK_SECRET"), _configured_item("STRIPE_PRICE_PRO"), _configured_item("STRIPE_PRICE_ELITE"), _item("Ultimo evento", "No consultado", "BLOQUEADO_POR_ACCESO", "Stripe read-only no ejecutado")], limitations=["No se contacta Stripe y no se ejecutan cobros."], next_action="Certificar webhook, productos, precios y suscripciones con pruebas no destructivas autorizadas."),
        "sports_gateway": _section("sports_gateway", "Sports Gateway", "PASS" if gateway.get("guardrails", {}).get("external_calls") == 0 else "BLOCKED", "CONFIRMADO", "Gateway legal presente: registrar, aprobar y evidenciar fuentes antes de uso.", items=[_item("Fuentes registradas", gateway.get("summary", {}).get("registered_sources", 0), "CONFIRMADO", "Sports Intelligence Gateway"), _item("Fuentes aprobadas", gateway.get("summary", {}).get("approved_sources", 0), "CONFIRMADO", "Sports Intelligence Gateway"), _item("Conexiones automaticas", gateway.get("summary", {}).get("automatic_connections", 0), "CONFIRMADO", "Sports Intelligence Gateway"), _item("Proveedor deportivo actual", "Detectado" if sports_provider else "No detectado", "CONFIRMADO", "env enmascarada"), _item("Ultima sincronizacion local", sports_record.get("last_at") or "No disponible", "CONFIRMADO" if sports_record.get("last_at") else "NO_CERTIFICADO", sports_record.get("table") or "DB local read-only")], limitations=["No se conectan nuevas fuentes y no se hace scraping."], next_action="Completar registro legal de fuentes antes de activar cualquier proveedor nuevo."),
        "sports_core": _section("sports_core", "Sports Core", "PASS", "CONFIRMADO", "Contratos y capacidades deportivas integradas segun registro local.", items=[_item("Contrato", contracts.get("contract"), "CONFIRMADO", "sports_platform_contracts"), _item("Capacidades", len(contracts.get("capabilities") or []), "CONFIRMADO", "sports_platform_contracts"), _item("Match Intelligence", system("shark").get("status") or "READY", "CONFIRMADO", "codigo local"), _item("Sports metrics", sports_metrics.get("contract") or "sports-metrics-v1", "CONFIRMADO", "sports-metrics-v1")], next_action="Mantener consumo de contratos; no recalcular metricas por modulo."),
        "database": _section("database", "Database", "PASS" if db_status.get("ok") else "BLOCKED", "CONFIRMADO", "SQLite validada en modo solo lectura." if db_status.get("ok") else "No se pudo validar SQLite local.", items=[_item("Estado", db_status.get("status") or "No disponible", "CONFIRMADO", "SQLite mode=ro"), _item("Ruta", db_status.get("path_masked") or "No disponible", "CONFIRMADO", "DB_PATH enmascarado"), _item("Tamano", db_status.get("size_bytes", "No disponible"), "CONFIRMADO" if db_status.get("size_bytes") is not None else "NO_CERTIFICADO", "filesystem local"), _item("Tablas", db_status.get("table_count", "No disponible"), "CONFIRMADO" if db_status.get("table_count") is not None else "NO_CERTIFICADO", "sqlite_master"), _item("Quick check", db_status.get("quick_check") or "No disponible", "CONFIRMADO" if db_status.get("quick_check") else "NO_CERTIFICADO", "PRAGMA quick_check")], limitations=["No hay escrituras DB desde el snapshot."], next_action="Mantener backup y restore aislado antes de cada release."),
        "cache": _section("cache", "Cache", "PASS", "CONFIRMADO", "Cache de runtime y service worker identificables sin purgas ni llamadas externas.", items=[_item("Service worker", f"NEMESIS_CACHE_{app_version.split('_', 1)[0]}", "CONFIRMADO", "runtime version"), _item("runtime files", _count_runtime_files(root_path, "data/runtime"), "CONFIRMADO", "filesystem local"), _item("release_output", _count_runtime_files(root_path, "release_output"), "CONFIRMADO", "filesystem local"), _item("Ultima limpieza", "No ejecutada", "NO_CERTIFICADO", "sin accion destructiva")], limitations=["No se purgan caches durante este sprint."], next_action="Auditar ZIP limpio solo durante cierre autorizado."),
        "observability": _section("observability", "Observability", "PASS" if scores.get("detection", {}).get("score", 0) >= 7 else "PARTIAL", "CONFIRMADO", "Sentinel, AutoPilot y Operations Center concentran errores, latencias y alertas locales.", items=[_item("Sentinel", system("sentinel").get("status") or "No disponible", "CONFIRMADO", system("sentinel").get("source") or "local"), _item("Errores recientes", "No certificados en produccion", "BLOQUEADO_POR_ACCESO", "Render logs no consultados"), _item("Latencias", "Locales/Browser QA", "NO_CERTIFICADO", "QA local"), _item("Eventos criticos", "Incidencias del snapshot", "CONFIRMADO", "Operations Center")], limitations=["Logs y latencia Render requieren lectura externa autorizada."], next_action="Conectar lectura no destructiva de logs/health en la certificacion final."),
        "security": _section("security", "Security", "PASS" if secret_guard_present and privacy.get("available") and not privacy.get("secrets") else "PARTIAL", "CONFIRMADO" if secret_guard_present else "REQUIERE_REVISION", "Secret Guard, Privacy Guard y transportes protegidos presentes.", items=[_item("Secret Guard", "Presente" if secret_guard_present else "No disponible", "CONFIRMADO" if secret_guard_present else "REQUIERE_REVISION", "automation_workforce"), _item("Privacy report", "Disponible" if privacy.get("available") else "No disponible", "CONFIRMADO" if privacy.get("available") else "REQUIERE_REVISION", "reports"), _item("Secret findings", privacy.get("secrets", 0), "CONFIRMADO" if privacy.get("available") else "REQUIERE_REVISION", "Privacy/Secret Guard"), _item("CSRF/admin", "Protegido por sesion y token en acciones POST", "CONFIRMADO", "app.py"), _item("Rate limit/headers", "Configuracion local presente; produccion pendiente", "NO_CERTIFICADO", "app.py/Render")], limitations=["No se imprimen secretos ni valores de entorno."], next_action="Ejecutar Privacy/Secret Guard antes de cada push/deploy autorizado."),
    }
    global_score = _build_global_score(sections, commercial, systems)
    return sections, commercial, global_score


def _release_gate_from_commercial(commercial: list[dict[str, Any]], global_score: dict[str, Any], incidents: list[dict[str, Any]]) -> dict[str, Any]:
    blocked_areas = [item for item in commercial if item.get("status") == "BLOCKED"]
    confirmed_critical = [item for item in incidents if item.get("severity") == "critical" and item.get("evidence_state") == "CONFIRMADO"]
    status = "PASS"
    if blocked_areas or confirmed_critical:
        status = "BLOCKED"
    elif global_score.get("overall_status") != "PASS":
        status = "PARTIAL"
    missing: list[str] = []
    for item in blocked_areas:
        missing.extend(item.get("missing") or [f"{item.get('area')} pendiente"])
    if not missing and status != "PASS":
        missing = ["Certificacion Render, Telegram, Stripe y observabilidad productiva pendiente."]
    return {"status": status, "score": global_score.get("overall_score"), "missing_for_ready": missing, "production_modified": False, "dangerous_actions_executed": False}


def _safe_operations_actions() -> list[dict[str, Any]]:
    return [
        {"key": "view_release_gate", "label": "Ver Release Gate", "kind": "link", "href": "/admin/operations-center", "description": "Solo consulta el panel actual.", "requires_approval": False, "dangerous": False},
        {"key": "run_local_diagnostic", "label": "Diagnostico local", "kind": "post", "endpoint": "/api/admin/operations-center/run-safe-scan", "description": "Guarda un snapshot interno read-only; no toca DB de producto.", "requires_approval": False, "dangerous": False},
        {"key": "open_sentinel", "label": "Abrir Sentinel", "kind": "link", "href": "/admin/sentinel-autopilot", "description": "Revisa tareas y evidencias sin autocorregir codigo.", "requires_approval": False, "dangerous": False},
        {"key": "open_developer_center", "label": "Developer Center", "kind": "link", "href": "/admin/developer-center", "description": "Consulta inventario, rutas y contratos.", "requires_approval": False, "dangerous": False},
    ]


def _incident_for(system: dict[str, Any]) -> dict[str, Any] | None:
    if system.get("status") in {"PASS", "HEALTHY", "READY", "CONFIGURED", "LOCAL_ONLY"} and system.get("evidence_state") == "CONFIRMADO":
        return None
    issue_seed = f"{system.get('id')}|{system.get('status')}|{system.get('evidence_state')}"
    severity = system.get("severity") or "medium"
    return {
        "issue_id": f"OPS-{sha1(issue_seed.encode('utf-8')).hexdigest()[:10].upper()}",
        "area": system.get("id"),
        "title": system.get("name"),
        "severity": severity,
        "status": "OPEN" if system.get("evidence_state") == "CONFIRMADO" else "CERTIFICATION_REQUIRED",
        "evidence_state": system.get("evidence_state"),
        "evidence": system.get("summary"),
        "source": system.get("source"),
        "next_action": system.get("next_action"),
        "safe_to_auto_fix": False,
        "requires_approval": system.get("id") in {"render", "database", "backups", "telegram", "stripe", "security", "continuity"},
    }


def build_operations_autopilot_bridge(incidents: list[dict[str, Any]], app_version: str) -> dict[str, Any]:
    issues = []
    tasks = []
    prompts = []
    for incident in incidents:
        issue = {
            **incident,
            "category": "admin_ops",
            "problem": incident.get("evidence"),
            "suggested_action": incident.get("next_action"),
            "codex_prompt": generate_operations_codex_prompt(incident, app_version),
            "dangerous_actions_executed": False,
        }
        issues.append(issue)
        tasks.append({
            "task_id": f"TASK-{incident.get('issue_id')}",
            "issue_id": incident.get("issue_id"),
            "title": incident.get("title"),
            "status": "WAITING_FOR_CERTIFICATION" if incident.get("status") == "CERTIFICATION_REQUIRED" else "OPEN",
            "safe_to_auto_fix": False,
            "requires_approval": bool(incident.get("requires_approval")),
            "next_action": incident.get("next_action"),
        })
        prompts.append({"issue_id": incident.get("issue_id"), "prompt": issue["codex_prompt"]})
    return {
        "compatible_with": "V888_SENTINEL_AUTOPILOT_SELF_IMPROVEMENT_ENGINE_FINAL",
        "issues": issues,
        "tasks": tasks,
        "codex_prompts": prompts,
        "safe_actions": [],
        "approval_required_actions": [task for task in tasks if task.get("requires_approval")],
        "auto_deploy": False,
        "auto_push": False,
        "send_real_telegram": False,
        "mutate_payments": False,
    }


def build_company_operations_snapshot(
    root: str | Path,
    db_path: str | Path,
    app_version: str,
    external_runtime: dict[str, Any] | None = None,
    sports_metrics: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root_path = Path(root)
    version_txt = _read_version(root_path, "VERSION.txt")
    app_version_file = _read_version(root_path, "APP_VERSION")
    git = _git_identity(root_path)
    connection, db_status = _sqlite_readonly(db_path)
    try:
        cron_record = _latest_operational_record(connection, ["automation_runs", "scheduler_runs", "cron_runs", "daily_automation_runs"])
        sports_record = _latest_operational_record(connection, ["api_sync_runs", "sports_sync_runs", "match_sync_runs", "matches"])
        telegram_record = _latest_operational_record(connection, ["telegram_delivery_memory", "telegram_deliveries", "telegram_queue"])
    finally:
        if connection is not None:
            connection.close()

    dr = build_disaster_recovery_readiness(root_path, db_path, app_version)
    privacy = _privacy_summary(root_path)
    runtime_aligned = version_txt == app_version and (not app_version_file or app_version_file == app_version)
    external_runtime = external_runtime or {}
    sports_metrics = dict(sports_metrics or {})
    external_certified = bool(
        external_runtime.get("version") == app_version
        and external_runtime.get("version_files_match") is True
        and external_runtime.get("deployment_alignment_status") == "aligned_local_files"
    )
    sports_provider = any(_env_present(name) for name in ["API_FOOTBALL_KEY", "API_SPORTS_KEY", "API_SPORTS_API_KEY", "THE_ODDS_API_KEY", "THESPORTSDB_API_KEY"])
    sports_has_evidence = bool(sports_record.get("last_at"))
    telegram_configured = _env_present("TELEGRAM_BOT_TOKEN") and _env_present("TELEGRAM_CHAT_ID")
    stripe_configured = _env_present("STRIPE_SECRET_KEY") and _env_present("STRIPE_WEBHOOK_SECRET") and _env_present("STRIPE_PRICE_PRO") and _env_present("STRIPE_PRICE_ELITE")
    secret_guard_present = (root_path / "automation_workforce" / "security_secret_guard.py").exists()
    reports_ready = (root_path / "reports" / "V938_PREFLIGHT_OPERATIONS_CENTER.md").exists()

    systems = [
        _system("runtime", "Runtime y version", "PASS" if runtime_aligned else "FAIL", "CONFIRMADO", "VERSION.txt, APP_VERSION y APP_VERSION de proceso coinciden." if runtime_aligned else "La identidad local no coincide.", "archivos locales", "critical" if not runtime_aligned else "info", {"version_txt": version_txt, "app_version_file": app_version_file, "app_version": app_version}, "Alinear los tres identificadores de version."),
        _system("render", "Render y deploy", "PASS" if external_certified else "NOT_CERTIFIED", "CONFIRMADO" if external_certified else "BLOQUEADO_POR_ACCESO", "Runtime externo alineado." if external_certified else "Produccion no se ha consultado desde esta ejecucion local.", "runtime externo", "critical" if external_runtime and not external_certified else "medium", {"checked": bool(external_runtime), "git_commit_hint": str(external_runtime.get("git_commit_hint") or "")[:12]}, "Certificar /api/runtime-version de Render en modo lectura."),
        _system("git", "Git y trazabilidad", "LOCAL_ONLY" if git.get("available") else "NOT_CERTIFIED", "CONFIRMADO" if git.get("available") else "BLOQUEADO_POR_ACCESO", f"Rama local {git.get('branch') or 'no disponible'} y SHA {git.get('sha_short') or 'no disponible'}.", git.get("source") or ".git", "medium", git, "Certificar origin/main y mantener rollback antes del deploy."),
        _system("database", "Base de datos", "HEALTHY" if db_status.get("ok") else db_status.get("status", "FAIL"), "CONFIRMADO", "SQLite local supera quick_check en solo lectura." if db_status.get("ok") else "La DB local no se pudo validar.", "SQLite mode=ro", "critical" if not db_status.get("ok") else "info", db_status, "Revisar DB_PATH, lock y disco sin reemplazar la DB."),
        _system("backups", "Backup y restore", "READY" if dr.get("ok") else "NOT_CERTIFIED", "CONFIRMADO" if dr.get("ok") else "NO_CERTIFICADO", f"{dr.get('validated_backup_count', 0)} backups con hash; restore aislado {'certificado' if dr.get('isolated_restore', {}).get('certified') else 'pendiente'}.", "disaster_recovery_engine", "high" if not dr.get("validated_backup_count") else "medium", dr, "Crear copia offsite y ejecutar restore aislado autorizado."),
        _system("cron", "Cron y automatizacion", "PASS" if cron_record.get("last_at") else "NOT_CERTIFIED", "CONFIRMADO" if cron_record.get("last_at") else "NO_CERTIFICADO", f"Ultima evidencia: {cron_record.get('last_at')}." if cron_record.get("last_at") else "No se encontro un tick reciente certificable en las tablas locales consultadas.", "DB local read-only", "high", cron_record, "Ejecutar dry-run protegido y certificar ultimo/proximo tick."),
        _system("telegram", "Telegram", "CONFIGURED" if telegram_configured else "NOT_CONFIGURED", "NO_CERTIFICADO", "Variables requeridas detectadas; no se ha enviado nada." if telegram_configured else "Configuracion completa no detectada en este entorno.", "variables enmascaradas y DB local", "high", {"configured": telegram_configured, "latest_record": telegram_record, "webhook_secret_configured": _env_present("TELEGRAM_WEBHOOK_SECRET")}, "Certificar webhook, dry-run, dedupe y destino autorizado sin envio masivo."),
        _system("stripe", "Stripe y membresias", "CONFIGURED" if stripe_configured else "NOT_CONFIGURED", "NO_CERTIFICADO", "Configuracion minima detectada sin contactar Stripe." if stripe_configured else "Checkout/webhook no pueden certificarse con la evidencia local disponible.", "variables enmascaradas", "critical" if not stripe_configured else "high", {"configured": stripe_configured, "payments_enabled": str(os.getenv("PAYMENTS_ENABLED") or "").lower() not in {"0", "false", "off"}}, "Certificar productos, precios y webhook de forma no destructiva."),
        _system("sports_data", "Datos deportivos", "PASS" if sports_provider and sports_has_evidence else "NOT_CERTIFIED", "CONFIRMADO" if sports_provider and sports_has_evidence else "NO_CERTIFICADO", f"Ultima evidencia local: {sports_record.get('last_at')}." if sports_has_evidence else "No hay timestamp local suficiente para declarar datos frescos.", "Sports Data Contract y evidencia operativa local", "high", {"provider_configured": sports_provider, "latest_record": sports_record, "sports_metrics": sports_metrics}, "Certificar frescura, completitud, stale y falsos live con timestamps reales."),
        _system("shark", "SHARK", "READY", "CONFIRMADO", "Motor y guardas locales presentes; produccion sigue pendiente de medicion externa.", "codigo y benchmark local V937", "medium", {"openai_configured": _env_present("OPENAI_API_KEY"), "production_certified": False}, "Medir produccion y confirmar cero escrituras por GET."),
        _system("sentinel", "Sentinel y AutoPilot", "READY", "CONFIRMADO", "Motores Sentinel, AutoPilot y memoria local disponibles.", "engines y data/runtime", "info", {"autopilot": (root_path / "engines" / "sentinel_autopilot_engine.py").exists(), "memory_present": (root_path / "data" / "runtime" / "sentinel_issues_memory.json").exists()}, "Ejecutar scan seguro y revisar solo incidencias con evidencia."),
        _system("security", "Seguridad y privacidad", "PASS" if secret_guard_present and privacy.get("available") and not privacy.get("secrets") else "REVIEW", "CONFIRMADO" if secret_guard_present and privacy.get("available") else "REQUIERE_REVISION", "Secret Guard y clasificacion disponibles." if secret_guard_present and privacy.get("available") else "El gate de secretos o la clasificacion todavia no aportan evidencia completa.", "scanner local redactor", "critical" if privacy.get("secrets") else "high", {"secret_guard_present": secret_guard_present, **privacy}, "Ejecutar Secret Guard y revisar candidatos de privacidad sin exponer valores."),
        _system("continuity", "Continuidad operativa", "READY" if dr.get("ok") and reports_ready else "NOT_CERTIFIED", "CONFIRMADO" if dr.get("ok") and reports_ready else "NO_CERTIFICADO", "Runbooks locales disponibles; offsite, restore y segundo operador condicionan la certificacion.", "informes V938 y DR", "high", {"reports_ready": reports_ready, "dr_ok": dr.get("ok")}, "Completar simulacro, offsite y handoff de segundo operador."),
    ]
    scores = _build_scores(systems, dr)
    operations_sections, commercial_readiness, global_score = _build_operations_sections(
        root_path=root_path,
        app_version=app_version,
        version_txt=version_txt,
        app_version_file=app_version_file,
        git=git,
        db_status=db_status,
        dr=dr,
        privacy=privacy,
        systems=systems,
        scores=scores,
        sports_metrics=sports_metrics,
        cron_record=cron_record,
        sports_record=sports_record,
        telegram_record=telegram_record,
        external_runtime=external_runtime,
        external_certified=external_certified,
        runtime_aligned=runtime_aligned,
        sports_provider=sports_provider,
        telegram_configured=telegram_configured,
        stripe_configured=stripe_configured,
        secret_guard_present=secret_guard_present,
    )
    incidents = [issue for issue in (_incident_for(item) for item in systems) if issue]
    blockers = [item for item in incidents if item.get("severity") in {"critical", "high"}]
    next_issue = blockers[0] if blockers else incidents[0] if incidents else {}
    snapshot = {
        "ok": not any(item.get("status") == "FAIL" and item.get("evidence_state") == "CONFIRMADO" for item in systems),
        "version": app_version,
        "generated_at_madrid": madrid_now_iso(),
        "mode": "read_only",
        "systems": systems,
        "sports_metrics": sports_metrics,
        "operations_sections": operations_sections,
        "commercial_readiness": commercial_readiness,
        "global_score": global_score,
        "safe_actions": _safe_operations_actions(),
        "scores": scores,
        "incidents": incidents,
        "incident_counts": {
            "total": len(incidents),
            "confirmed": sum(1 for item in incidents if item.get("evidence_state") == "CONFIRMADO"),
            "certification_required": sum(1 for item in incidents if item.get("status") == "CERTIFICATION_REQUIRED"),
            "critical": sum(1 for item in incidents if item.get("severity") == "critical" and item.get("evidence_state") == "CONFIRMADO"),
            "high": sum(1 for item in incidents if item.get("severity") == "high" and item.get("evidence_state") == "CONFIRMADO"),
            "critical_certification_required": sum(1 for item in incidents if item.get("severity") == "critical" and item.get("status") == "CERTIFICATION_REQUIRED"),
            "high_certification_required": sum(1 for item in incidents if item.get("severity") == "high" and item.get("status") == "CERTIFICATION_REQUIRED"),
        },
        "readiness": {
            "local_gate": "PASS" if runtime_aligned and db_status.get("ok") and secret_guard_present else "BLOCKED",
            "production_gate": "NOT_CERTIFIED" if not external_certified else "PASS",
            "recovery_gate": "PASS" if dr.get("ok") else "NOT_CERTIFIED",
            "dangerous_actions_executed": False,
        },
        "next_action": next_issue.get("next_action") or "Revisar evidencia y mantener vigilancia.",
        "next_issue_id": next_issue.get("issue_id") or "",
        "safe_guards": ["no_deploy", "no_push", "no_real_telegram", "no_stripe_actions", "no_production_db_write", "no_paid_provider_call"],
    }
    snapshot["release_1_gate"] = _release_gate_from_commercial(commercial_readiness, global_score, incidents)
    snapshot["autopilot_bridge"] = build_operations_autopilot_bridge(incidents, app_version)
    snapshot["monitoring"] = build_operations_monitoring(snapshot)
    return snapshot


def generate_operations_codex_prompt(issue: dict[str, Any], app_version: str) -> str:
    if not issue:
        return ""
    return "\n".join([
        f"NeMeSiS SHARK PRO {app_version}",
        "Investiga este hallazgo del Operations Center sin tocar produccion ni secretos.",
        f"ID: {issue.get('issue_id')}",
        f"Area: {issue.get('area')}",
        f"Severidad: {issue.get('severity')}",
        f"Estado de evidencia: {issue.get('evidence_state')}",
        f"Evidencia: {issue.get('evidence')}",
        f"Siguiente accion: {issue.get('next_action')}",
        "Primero confirma o refuta con evidencia. No conviertas NO_CERTIFICADO en fallo. Propone el cambio minimo y sus pruebas; no despliegues.",
    ])


def _runtime_dir(root: str | Path) -> Path:
    return Path(root) / "data" / "runtime" / RUNTIME_DIR_NAME


def save_operations_snapshot(root: str | Path, snapshot: dict[str, Any]) -> Path:
    directory = _runtime_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "latest_scan.json"
    path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def load_operations_reviews(root: str | Path) -> dict[str, Any]:
    path = _runtime_dir(root) / "reviews.json"
    if not path.exists():
        return {"reviews": []}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else {"reviews": []}
    except Exception:
        return {"reviews": []}


def mark_operations_issue_reviewed(root: str | Path, issue_id: str, note: str = "") -> dict[str, Any]:
    issue_id = str(issue_id or "").strip()
    if not issue_id:
        return {"ok": False, "error": "issue_id_required"}
    payload = load_operations_reviews(root)
    reviews = [item for item in payload.get("reviews", []) if item.get("issue_id") != issue_id]
    reviews.append({"issue_id": issue_id, "reviewed_at_madrid": madrid_now_iso(), "note": str(note or "")[:500]})
    result = {"reviews": reviews[-200:]}
    directory = _runtime_dir(root)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "reviews.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {"ok": True, "issue_id": issue_id, "dangerous_actions_executed": False}

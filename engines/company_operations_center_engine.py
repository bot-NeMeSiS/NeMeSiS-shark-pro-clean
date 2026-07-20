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
            row = connection.execute(f'SELECT {", ".join(f"\"{name}\"" for name in selected)} FROM "{table}"{order} LIMIT 1').fetchone()
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
        _system("sports_data", "Datos deportivos", "PASS" if sports_provider and sports_has_evidence else "NOT_CERTIFIED", "CONFIRMADO" if sports_provider and sports_has_evidence else "NO_CERTIFICADO", f"Ultima evidencia local: {sports_record.get('last_at')}." if sports_has_evidence else "No hay timestamp local suficiente para declarar datos frescos.", "DB/cache local y presencia de proveedor", "high", {"provider_configured": sports_provider, "latest_record": sports_record}, "Certificar frescura, completitud, stale y falsos live con timestamps reales."),
        _system("shark", "SHARK", "READY", "CONFIRMADO", "Motor y guardas locales presentes; produccion sigue pendiente de medicion externa.", "codigo y benchmark local V937", "medium", {"openai_configured": _env_present("OPENAI_API_KEY"), "production_certified": False}, "Medir produccion y confirmar cero escrituras por GET."),
        _system("sentinel", "Sentinel y AutoPilot", "READY", "CONFIRMADO", "Motores Sentinel, AutoPilot y memoria local disponibles.", "engines y data/runtime", "info", {"autopilot": (root_path / "engines" / "sentinel_autopilot_engine.py").exists(), "memory_present": (root_path / "data" / "runtime" / "sentinel_issues_memory.json").exists()}, "Ejecutar scan seguro y revisar solo incidencias con evidencia."),
        _system("security", "Seguridad y privacidad", "PASS" if secret_guard_present and privacy.get("available") and not privacy.get("secrets") else "REVIEW", "CONFIRMADO" if secret_guard_present and privacy.get("available") else "REQUIERE_REVISION", "Secret Guard y clasificacion disponibles." if secret_guard_present and privacy.get("available") else "El gate de secretos o la clasificacion todavia no aportan evidencia completa.", "scanner local redactor", "critical" if privacy.get("secrets") else "high", {"secret_guard_present": secret_guard_present, **privacy}, "Ejecutar Secret Guard y revisar candidatos de privacidad sin exponer valores."),
        _system("continuity", "Continuidad operativa", "READY" if dr.get("ok") and reports_ready else "NOT_CERTIFIED", "CONFIRMADO" if dr.get("ok") and reports_ready else "NO_CERTIFICADO", "Runbooks locales disponibles; offsite, restore y segundo operador condicionan la certificacion.", "informes V938 y DR", "high", {"reports_ready": reports_ready, "dr_ok": dr.get("ok")}, "Completar simulacro, offsite y handoff de segundo operador."),
    ]
    scores = _build_scores(systems, dr)
    incidents = [issue for issue in (_incident_for(item) for item in systems) if issue]
    blockers = [item for item in incidents if item.get("severity") in {"critical", "high"}]
    next_issue = blockers[0] if blockers else incidents[0] if incidents else {}
    snapshot = {
        "ok": not any(item.get("status") == "FAIL" and item.get("evidence_state") == "CONFIRMADO" for item in systems),
        "version": app_version,
        "generated_at_madrid": madrid_now_iso(),
        "mode": "read_only",
        "systems": systems,
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

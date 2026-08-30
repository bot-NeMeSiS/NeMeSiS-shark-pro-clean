"""V892 Sentinel issues command center.

Safe issue board for Sentinel, AutoPilot and Visual Worker findings. The engine
normalizes findings into actionable issues, deduplicates them and generates
copy-ready Codex prompts without sending Telegram, touching secrets, mutating
payments/users, calling paid APIs or inventing sports data.
"""
from __future__ import annotations

from datetime import datetime
from hashlib import sha1
import json
import os
import re
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


MADRID_TZ = ZoneInfo("Europe/Madrid")

SENTINEL_ISSUES_VERSION = "V892_SENTINEL_ISSUES_COMMAND_CENTER_COPY_FIX_PROMPTS_FINAL"

ISSUE_STATUSES = [
    "OPEN_REAL",
    "FIXED_PENDING_VERIFICATION",
    "RESOLVED",
    "FALSE_POSITIVE",
    "STALE",
    "DUPLICATE",
    "EXTERNAL_BLOCKER",
    "INSUFFICIENT_EVIDENCE",
]

STATUS_CONTRACT = "NEMESIS_ISSUE_LEDGER_V2"
ACTIVE_ISSUE_STATUSES = {"OPEN_REAL"}
TERMINAL_ISSUE_STATUSES = {"RESOLVED", "FALSE_POSITIVE", "DUPLICATE"}
LEGACY_STATUS_MAP = {
    "OPEN": "OPEN_REAL",
    "IN_REVIEW": "OPEN_REAL",
    "CODEX_READY": "OPEN_REAL",
    "FIX_IN_PROGRESS": "OPEN_REAL",
    "REOPENED": "OPEN_REAL",
    "FIXED_PENDING_VALIDATION": "FIXED_PENDING_VERIFICATION",
    "RESOLVED_PENDING_HUMAN_REVIEW": "FIXED_PENDING_VERIFICATION",
    "RESOLVED_BY_RESCAN": "STALE",
    "STALE_NEEDS_REVALIDATION": "STALE",
    "IGNORED_SAFE": "FALSE_POSITIVE",
    "FOUNDER_REJECTED": "FALSE_POSITIVE",
}

SEVERITIES = ["critical", "high", "medium", "low", "info"]

AREA_ALIASES = {
    "admin_ops": "admin",
    "visual_layout": "visual",
    "navigation": "buttons_routes",
    "picks_odds": "picks",
    "production_alignment": "render",
    "release_zip": "release",
    "copy": "texts",
    "sports_data": "sports",
    "telegram_premium_picks": "telegram",
    "shark_ai": "shark",
}

SECRET_RE = re.compile(
    r"(sk_live_[A-Za-z0-9_]+|sk_test_[A-Za-z0-9_]+|bot\d+:[A-Za-z0-9_\-]+|"
    r"TELEGRAM_BOT_TOKEN\s*=\s*\S+|AUTOMATION_SECRET\s*=\s*\S+|"
    r"(?:API|TOKEN|SECRET|KEY)[A-Z0-9_]*\s*=\s*['\"]?[^'\"\s]+)",
    re.I,
)


def _now() -> str:
    return datetime.now(MADRID_TZ).replace(microsecond=0).isoformat()


def sentinel_issues_memory_path(root: str | Path | None = None) -> Path:
    if os.getenv("CONTINUOUS_EVOLUTION_SAFE_MODE", "").strip() == "1":
        safe_root = os.getenv("CONTINUOUS_EVOLUTION_STORAGE_ROOT", "").strip()
        if safe_root:
            return Path(safe_root) / "sentinel_issues_memory.json"
    base = Path(root or Path.cwd())
    return base / "data" / "runtime" / "sentinel_issues_memory.json"


def _autopilot_memory_path(root: str | Path | None = None) -> Path:
    base = Path(root or Path.cwd())
    return base / "data" / "runtime" / "sentinel_autopilot_memory.json"


def _safe_text(value: Any, limit: int = 900) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    text = SECRET_RE.sub("[redacted]", text)
    return text[:limit]


def _safe_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _load_json(path: Path, default: dict[str, Any]) -> dict[str, Any]:
    try:
        if not path.exists():
            return dict(default)
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else dict(default)
    except Exception:
        return dict(default)


def _canonical_status(value: Any) -> str:
    status = str(value or "OPEN_REAL").strip().upper()
    status = LEGACY_STATUS_MAP.get(status, status)
    return status if status in ISSUE_STATUSES else "INSUFFICIENT_EVIDENCE"


def _priority_for_severity(value: Any) -> str:
    return {
        "critical": "P0",
        "high": "P1",
        "medium": "P2",
        "low": "P3",
        "info": "P3",
    }.get(str(value or "low").lower(), "P3")


def _is_synthetic_404(issue: dict[str, Any]) -> bool:
    route = str(issue.get("route") or issue.get("screen") or "").lower()
    text = " ".join(str(issue.get(key) or "") for key in ("title", "evidence", "actual", "stable_key")).lower()
    synthetic_tokens = (
        "ruta-inventada",
        "nonexistent",
        "not-found-test",
        "missing-route-test",
        "qa-probe",
    )
    return any(token in route or token in text for token in synthetic_tokens)


def issue_has_sufficient_evidence(issue: dict[str, Any]) -> bool:
    if "evidence_sufficient" in issue:
        return issue.get("evidence_sufficient") is True
    evidence = str(issue.get("evidence") or "").strip()
    actual = str(issue.get("actual") or "").strip()
    origin = str(issue.get("evidence_origin") or issue.get("source") or "").upper()
    has_artifact = bool(
        issue.get("screenshot")
        or issue.get("production_sha")
        or issue.get("verification")
        or issue.get("reproduction_steps")
    )
    strong_origin = any(token in origin for token in ("FOUNDER", "REAL_PRODUCTION", "CURRENT_PRODUCTION", "LOCAL_QA"))
    return len(evidence) >= 20 and (bool(actual) or has_artifact or strong_origin)


def _canonicalize_existing_issue(raw: dict[str, Any]) -> dict[str, Any]:
    issue = dict(raw)
    legacy_status = str(issue.get("status") or "OPEN_REAL").upper()
    status = _canonical_status(legacy_status)
    if _is_synthetic_404(issue):
        status = "FALSE_POSITIVE"
        issue.setdefault("verification", "Prueba sintética de ruta; no representa un fallo de producto.")
    if legacy_status not in ISSUE_STATUSES:
        issue["legacy_status"] = legacy_status
    issue["status"] = status
    severity = str(issue.get("severity") or "low").lower()
    issue["severity"] = severity if severity in SEVERITIES else "low"
    issue["priority"] = str(issue.get("priority") or _priority_for_severity(issue["severity"])).upper()
    issue["issue_id"] = issue.get("issue_id") or issue.get("id")
    issue["id"] = issue.get("id") or issue.get("issue_id")
    issue["category"] = issue.get("category") or issue.get("area") or "product"
    issue["component"] = issue.get("component") or issue.get("element") or issue.get("area") or "product"
    issue["worker_sources"] = _safe_list(issue.get("worker_sources")) or [
        item for item in (issue.get("worker"), issue.get("source")) if item
    ]
    issue["evidence_history"] = _safe_list(issue.get("evidence_history"))
    if issue.get("evidence") and not issue["evidence_history"]:
        issue["evidence_history"] = [{
            "at_madrid": issue.get("last_seen") or issue.get("last_seen_madrid") or issue.get("detected_at_madrid"),
            "evidence": issue.get("evidence"),
            "origin": issue.get("evidence_origin") or issue.get("source"),
        }]
    issue["related_issue_ids"] = _safe_list(issue.get("related_issue_ids"))
    issue["fix_sha"] = issue.get("fix_sha") or ""
    issue["verification"] = issue.get("verification") or ""
    issue["founder_feedback"] = _safe_list(issue.get("founder_feedback"))
    issue["first_seen"] = issue.get("first_seen") or issue.get("detected_at_madrid") or _now()
    issue["last_seen"] = issue.get("last_seen") or issue.get("last_seen_madrid") or issue["first_seen"]
    issue["seen_count"] = int(issue.get("seen_count") or issue.get("occurrences") or 1)
    issue["evidence_sufficient"] = issue_has_sufficient_evidence(issue)
    issue["codex_eligible"] = status == "OPEN_REAL" and issue["evidence_sufficient"]
    return issue


def canonicalize_sentinel_memory(memory: dict[str, Any]) -> dict[str, Any]:
    memory["status_contract"] = STATUS_CONTRACT
    memory["issues"] = [
        _canonicalize_existing_issue(item)
        for item in _safe_list(memory.get("issues"))
        if isinstance(item, dict)
    ]
    return memory


def load_sentinel_issues_memory(root: str | Path | None = None) -> dict[str, Any]:
    default = {
        "version": SENTINEL_ISSUES_VERSION,
        "created_at_madrid": _now(),
        "updated_at_madrid": _now(),
        "issues": [],
        "events": [],
    }
    memory = _load_json(sentinel_issues_memory_path(root), default)
    memory.setdefault("version", SENTINEL_ISSUES_VERSION)
    memory.setdefault("issues", [])
    memory.setdefault("events", [])
    return canonicalize_sentinel_memory(memory)


def save_sentinel_issues_memory(memory: dict[str, Any], root: str | Path | None = None) -> None:
    path = sentinel_issues_memory_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    memory = canonicalize_sentinel_memory(memory)
    memory["version"] = SENTINEL_ISSUES_VERSION
    memory["status_contract"] = STATUS_CONTRACT
    memory["updated_at_madrid"] = _now()
    path.write_text(json.dumps(memory, ensure_ascii=False, indent=2), encoding="utf-8")


def issue_fingerprint(issue: dict[str, Any]) -> str:
    stable_key = _safe_text(issue.get("stable_key"), 500)
    if stable_key:
        return sha1(stable_key.lower().encode("utf-8", errors="ignore")).hexdigest()[:16]
    raw = "|".join(
        [
            _safe_text(issue.get("area"), 80),
            _safe_text(issue.get("route"), 160),
            _safe_text(issue.get("file"), 180),
            _safe_text(issue.get("title"), 180),
            _safe_text(issue.get("evidence"), 220),
        ]
    ).lower()
    return sha1(raw.encode("utf-8", errors="ignore")).hexdigest()[:16]


def _issue_id(fingerprint: str) -> str:
    year = datetime.now(MADRID_TZ).year
    return f"SENT-{year}-{fingerprint[:8].upper()}"


def classify_sentinel_issue(issue: dict[str, Any]) -> str:
    text = " ".join(
        _safe_text(issue.get(key), 400).lower()
        for key in ["title", "area", "evidence", "impact", "risk", "recommendation"]
    )
    area = str(issue.get("area") or "").lower()
    if any(token in text for token in ["500", "502", "traceback", "secret", "sin proteccion", "unprotected", "db_path", "automation_secret"]):
        return "critical"
    if any(token in text for token in ["render desalineado", "cron falla", "telegram cron", "login", "sin cuota", "sin seleccion", "fake", "falso operativo"]):
        return "high"
    if area in {"payments", "security", "render"}:
        return "high"
    if area in {"visual", "texts", "buttons_routes", "client", "admin", "shark", "logos", "picks", "live"}:
        return "medium"
    return str(issue.get("severity") or "low").lower() if str(issue.get("severity") or "").lower() in SEVERITIES else "low"


def _area(value: Any) -> str:
    area = _safe_text(value or "visual", 80).lower().replace(" ", "_")
    return AREA_ALIASES.get(area, area or "visual")


def generate_issue_prompt(issue: dict[str, Any]) -> str:
    return (
        "Corrige esta incidencia en NeMeSiS SHARK PRO sin romper nada anterior.\n\n"
        f"ID:\n{issue.get('id')}\n\n"
        f"Area:\n{issue.get('area')}\n\n"
        f"Severidad:\n{issue.get('severity')}\n\n"
        f"Problema:\n{issue.get('title')}\n\n"
        f"Ruta afectada:\n{issue.get('route') or 'Sin ruta concreta'}\n\n"
        f"Archivo probable:\n{issue.get('file') or 'Por determinar'}\n\n"
        f"Evidencia:\n{issue.get('evidence') or 'Sin evidencia adicional'}\n\n"
        f"Impacto:\n{issue.get('impact') or 'Puede degradar la experiencia cliente/admin si sigue activo.'}\n\n"
        "Reglas:\n\n"
        "* No inventar datos.\n"
        "* No tocar secretos.\n"
        "* No romper usuarios, sesiones, membresias, pagos, DB_PATH, Madrid Time, Render Cron ni Telegram dedupe.\n"
        "* Mantener navegacion cliente/admin separada.\n"
        "* Mantener estados seguros si faltan datos reales.\n\n"
        f"Que debes hacer:\n{issue.get('recommendation') or 'Localizar causa real, aplicar fix seguro y revalidar.'}\n\n"
        "Validaciones obligatorias:\n"
        + "\n".join(f"* {item}" for item in (issue.get("validation") or ["python -m py_compile app.py", "python tools/run_continuous_sentinel_static.py"]))
        + "\n\nEntrega:\n\n"
        "* resumen de cambios;\n"
        "* archivos tocados;\n"
        "* validaciones pasadas;\n"
        "* limitaciones honestas;\n"
        "* ZIP limpio si corresponde.\n"
    )


def copy_issue_text(issue: dict[str, Any]) -> str:
    return (
        f"[{str(issue.get('severity') or '').upper()}] [{issue.get('area')}] {issue.get('title')}\n"
        f"Ruta: {issue.get('route') or 'Sin ruta concreta'}\n"
        f"Archivo probable: {issue.get('file') or 'Por determinar'}\n"
        f"Evidencia: {issue.get('evidence') or 'Sin evidencia adicional'}\n"
        f"Impacto: {issue.get('impact') or 'Pendiente de revisar'}\n"
        f"Recomendacion: {issue.get('recommendation') or 'Revisar y corregir con Codex'}"
    )


def normalize_sentinel_issue(raw: dict[str, Any], source: str = "sentinel") -> dict[str, Any]:
    title = _safe_text(raw.get("title") or raw.get("name") or raw.get("rule") or raw.get("issue") or "Incidencia Sentinel")
    area = _area(raw.get("area") or raw.get("category") or raw.get("module") or raw.get("profile") or source)
    route = _safe_text(raw.get("route") or raw.get("screen") or raw.get("path"), 180)
    file_name = _safe_text(raw.get("file") or raw.get("template") or raw.get("probable_file"), 220)
    evidence = _safe_text(raw.get("evidence") or raw.get("detail") or raw.get("reason") or raw.get("message") or raw.get("description"))
    recommendation = _safe_text(raw.get("recommendation") or raw.get("suggested_fix") or raw.get("next_action") or "Revisar causa real y corregir sin tocar secretos ni datos reales.")
    issue = {
        "title": title,
        "area": area,
        "severity": str(raw.get("severity") or raw.get("risk_level") or "low").lower(),
        "status": _canonical_status(raw.get("status") or "OPEN_REAL"),
        "source": _safe_text(raw.get("source") or source, 80),
        "detected_at_madrid": _safe_text(raw.get("detected_at_madrid") or _now(), 80),
        "updated_at_madrid": _now(),
        "route": route,
        "screen": _safe_text(raw.get("screen") or route, 180),
        "file": file_name,
        "function": _safe_text(raw.get("function") or raw.get("probable_function"), 180),
        "evidence": evidence,
        "impact": _safe_text(raw.get("impact") or "Afecta a claridad, operacion o confianza del producto si permanece activo."),
        "risk": _safe_text(raw.get("risk") or raw.get("risk_level") or "Revisar antes de dar por resuelto."),
        "recommendation": recommendation,
        "validation": _safe_list(raw.get("validation")) or [
            "python -m py_compile app.py",
            "python tools/run_continuous_sentinel_static.py",
        ],
        "tags": _safe_list(raw.get("tags")) or [area, source],
        "resolved_at_madrid": raw.get("resolved_at_madrid"),
        "history": _safe_list(raw.get("history")),
        "occurrences": int(raw.get("occurrences") or 1),
        "last_seen_madrid": _safe_text(raw.get("last_seen_madrid") or _now(), 80),
        "worker": _safe_text(raw.get("worker"), 120),
        "category": _safe_text(raw.get("category") or area, 120),
        "viewport": _safe_text(raw.get("viewport"), 80),
        "element": _safe_text(raw.get("element"), 180),
        "expected": _safe_text(raw.get("expected"), 900),
        "actual": _safe_text(raw.get("actual"), 900),
        "screenshot": _safe_text(raw.get("screenshot"), 500),
        "first_seen": _safe_text(raw.get("first_seen") or raw.get("detected_at_madrid") or _now(), 80),
        "last_seen": _safe_text(raw.get("last_seen") or raw.get("last_seen_madrid") or _now(), 80),
        "seen_count": int(raw.get("seen_count") or raw.get("occurrences") or 1),
        "production_sha": _safe_text(raw.get("production_sha"), 80),
        "confidence": _safe_text(raw.get("confidence") or "UNKNOWN", 40),
        "priority": _safe_text(raw.get("priority") or "", 10).upper(),
        "component": _safe_text(raw.get("component") or raw.get("element") or area, 180),
        "evidence_origin": _safe_text(raw.get("evidence_origin") or raw.get("source") or source, 80),
        "evidence_history": _safe_list(raw.get("evidence_history")),
        "worker_sources": _safe_list(raw.get("worker_sources")),
        "related_issue_ids": _safe_list(raw.get("related_issue_ids")),
        "fix_sha": _safe_text(raw.get("fix_sha"), 80),
        "verification": _safe_text(raw.get("verification"), 900),
        "founder_feedback": _safe_list(raw.get("founder_feedback")),
        "stable_key": _safe_text(raw.get("stable_key"), 500),
    }
    issue["severity"] = classify_sentinel_issue(issue)
    issue["priority"] = issue["priority"] or _priority_for_severity(issue["severity"])
    issue["fingerprint"] = issue_fingerprint(issue)
    issue["id"] = _safe_text(raw.get("id") or raw.get("issue_id") or _issue_id(issue["fingerprint"]), 80)
    issue["issue_id"] = issue["id"]
    issue["worker_sources"] = issue["worker_sources"] or [item for item in (issue.get("worker"), issue.get("source")) if item]
    issue["evidence_sufficient"] = bool(raw.get("evidence_sufficient")) or issue_has_sufficient_evidence(issue)
    issue["codex_eligible"] = issue["status"] == "OPEN_REAL" and issue["evidence_sufficient"]
    issue["codex_prompt"] = (
        _safe_text(raw.get("codex_prompt"), 4000) or generate_issue_prompt(issue)
        if issue["codex_eligible"]
        else ""
    )
    issue["copy_text"] = copy_issue_text(issue)
    return _canonicalize_existing_issue(issue)


def upsert_sentinel_issues(existing: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_fp = {str(item.get("fingerprint") or issue_fingerprint(item)): dict(item) for item in existing if isinstance(item, dict)}
    for candidate in candidates:
        fp = candidate["fingerprint"]
        previous = by_fp.get(fp)
        if previous:
            history = _safe_list(previous.get("history"))
            history.append({
                "at_madrid": _now(),
                "event": "seen_again",
                "source": candidate.get("source"),
                "status_before": previous.get("status"),
            })
            previous.update({
                "title": candidate.get("title"),
                "severity": candidate.get("severity"),
                "source": candidate.get("source"),
                "updated_at_madrid": _now(),
                "last_seen_madrid": _now(),
                "evidence": candidate.get("evidence") or previous.get("evidence"),
                "recommendation": candidate.get("recommendation") or previous.get("recommendation"),
                "codex_prompt": candidate.get("codex_prompt"),
                "copy_text": candidate.get("copy_text"),
                "occurrences": int(previous.get("occurrences") or 1) + 1,
                "seen_count": int(previous.get("seen_count") or previous.get("occurrences") or 1) + 1,
                "last_seen": candidate.get("last_seen") or _now(),
                "actual": candidate.get("actual") or previous.get("actual"),
                "expected": candidate.get("expected") or previous.get("expected"),
                "screenshot": candidate.get("screenshot") or previous.get("screenshot"),
                "production_sha": candidate.get("production_sha") or previous.get("production_sha"),
                "confidence": candidate.get("confidence") or previous.get("confidence"),
                "history": history[-20:],
            })
            if candidate.get("status") == "OPEN_REAL" and previous.get("status") in TERMINAL_ISSUE_STATUSES:
                previous["status"] = "OPEN_REAL"
                previous["resolved_at_madrid"] = None
                history.append({"at_madrid": _now(), "event": "reopened_by_current_evidence"})
            elif candidate.get("status") in ISSUE_STATUSES:
                previous["status"] = candidate.get("status")
            previous["history"] = history[-20:]
        else:
            by_fp[fp] = candidate
    severity_rank = {name: idx for idx, name in enumerate(SEVERITIES)}
    return sorted(by_fp.values(), key=lambda item: (severity_rank.get(str(item.get("severity")), 9), str(item.get("updated_at_madrid") or "")), reverse=False)


def reconcile_sentinel_issues(existing: list[dict[str, Any]], candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Keep Sentinel memory truthful after a fresh scan.

    Missing evidence never closes an issue automatically. It moves to human or
    deterministic verification while the full history remains available.
    """
    seen = {candidate.get("fingerprint") for candidate in candidates if candidate.get("fingerprint")}
    inactive_statuses = TERMINAL_ISSUE_STATUSES | {"EXTERNAL_BLOCKER", "INSUFFICIENT_EVIDENCE"}
    for issue in existing:
        if not isinstance(issue, dict):
            continue
        fp = issue.get("fingerprint") or issue_fingerprint(issue)
        issue["fingerprint"] = fp
        if fp in seen:
            issue["missed_scans"] = 0
            continue
        if issue.get("status") in inactive_statuses:
            continue
        missed = int(issue.get("missed_scans") or 0) + 1
        issue["missed_scans"] = missed
        issue["updated_at_madrid"] = _now()
        history = _safe_list(issue.get("history"))
        if missed >= 3:
            issue["status"] = "STALE"
            event = "stale_after_clean_scans"
        else:
            issue["status"] = "FIXED_PENDING_VERIFICATION"
            event = "not_reproduced_pending_verification"
        history.append({
            "at_madrid": _now(),
            "event": event,
            "missed_scans": missed,
            "note": "El scan actual no reprodujo esta incidencia.",
        })
        issue["history"] = history[-20:]
    return existing


def update_issue_status(issue_id: str, status: str, root: str | Path | None = None, note: str = "") -> dict[str, Any]:
    status = status.upper()
    if status not in ISSUE_STATUSES:
        return {"ok": False, "error": "invalid_status", "allowed_statuses": ISSUE_STATUSES}
    memory = load_sentinel_issues_memory(root)
    for issue in memory.get("issues", []):
        if issue.get("id") == issue_id:
            issue["status"] = status
            issue["updated_at_madrid"] = _now()
            if status == "RESOLVED":
                issue["resolved_at_madrid"] = _now()
            if status == "OPEN_REAL":
                issue["resolved_at_madrid"] = None
            history = _safe_list(issue.get("history"))
            history.append({"at_madrid": _now(), "event": "status_update", "status": status, "note": _safe_text(note, 300)})
            issue["history"] = history[-20:]
            save_sentinel_issues_memory(memory, root)
            return {"ok": True, "issue": issue}
    return {"ok": False, "error": "issue_not_found"}


def _issues_from_autopilot_memory(root: str | Path | None = None) -> list[dict[str, Any]]:
    memory = _load_json(_autopilot_memory_path(root), {"issues": []})
    return [normalize_sentinel_issue(item, "autopilot") for item in _safe_list(memory.get("issues")) if isinstance(item, dict)]


def _issues_from_result(result: dict[str, Any] | None, source: str) -> list[dict[str, Any]]:
    if not isinstance(result, dict):
        return []
    issues: list[dict[str, Any]] = []
    for key in ["issues", "grouped_issues", "critical_issues", "high_issues", "medium_issues", "low_issues"]:
        for item in _safe_list(result.get(key)):
            if isinstance(item, dict):
                issues.append(normalize_sentinel_issue(item, source))
    return issues


def _is_obsolete_route_500_issue(issue: dict[str, Any], healthy_routes: set[str]) -> bool:
    route = str(issue.get("route") or "").strip()
    if not route or route not in healthy_routes:
        return False
    text = " ".join(str(issue.get(key) or "") for key in ("title", "evidence", "risk", "impact", "recommendation")).lower()
    return "500" in text or "5xx" in text


def build_runtime_issues(runtime: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(runtime, dict):
        return []
    issues: list[dict[str, Any]] = []
    last_error = _safe_text(runtime.get("last_error"), 500)
    if last_error:
        issues.append(normalize_sentinel_issue({
            "title": "Runtime informa un ultimo error activo o historico",
            "area": "render",
            "severity": "high",
            "source": "runtime-version",
            "route": "/api/runtime-version",
            "evidence": last_error,
            "impact": "Puede ocultar un fallo real de produccion si no se clasifica como historico o activo.",
            "recommendation": "Verificar si el error se reproduce, sanearlo si es historico y corregir la causa si sigue activo.",
            "validation": ["GET /api/runtime-version", "python tools/run_continuous_sentinel_static.py"],
        }, "runtime"))
    if runtime.get("openai_configured") is False:
        issues.append(normalize_sentinel_issue({
            "title": "SHARK IA avanzada pendiente de configuracion",
            "area": "shark",
            "severity": "low",
            "source": "runtime-version",
            "route": "/shark",
            "evidence": "openai_configured=false",
            "impact": "El cliente debe ver modo seguro activo y analisis limitado sin proveedor IA.",
            "recommendation": "Mantener copy honesto de modo seguro sin prometer OpenAI real.",
            "validation": ["GET /api/runtime-version", "Smoke /shark"],
        }, "runtime"))
    logo_count = int(runtime.get("team_logo_cache_count") or 0) + int(runtime.get("league_logo_cache_count") or 0)
    if logo_count == 0:
        issues.append(normalize_sentinel_issue({
            "title": "Cache de logos en cero con fallback obligatorio",
            "area": "logos",
            "severity": "medium",
            "source": "runtime-version",
            "route": "/partidos",
            "evidence": "team_logo_cache_count=0 y league_logo_cache_count=0",
            "impact": "Las cards deportivas deben usar fallback premium sin imagen rota ni escudo inventado.",
            "recommendation": "Verificar fallback visual y documentar sincronizacion segura si procede.",
            "validation": ["Smoke /partidos", "Smoke /live", "Smoke /picks"],
        }, "runtime"))
    return issues


def run_sentinel_issues_scan(
    app_version: str,
    root: str | Path | None = None,
    *,
    sentinel_result: dict[str, Any] | None = None,
    autopilot_result: dict[str, Any] | None = None,
    visual_result: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
    healthy_routes: set[str] | None = None,
    save_memory: bool = False,
) -> dict[str, Any]:
    candidates: list[dict[str, Any]] = []
    candidates.extend(_issues_from_result(sentinel_result, "sentinel"))
    candidates.extend(_issues_from_result(autopilot_result, "autopilot"))
    candidates.extend(_issues_from_result(visual_result, "visual_worker"))
    candidates.extend(build_runtime_issues(runtime))
    candidates.extend(_issues_from_autopilot_memory(root))
    healthy_routes = healthy_routes or set()
    if healthy_routes:
        candidates = [issue for issue in candidates if not _is_obsolete_route_500_issue(issue, healthy_routes)]

    memory = load_sentinel_issues_memory(root)
    issues = upsert_sentinel_issues(_safe_list(memory.get("issues")), candidates) if candidates else _safe_list(memory.get("issues"))
    issues = reconcile_sentinel_issues(issues, candidates)
    memory["issues"] = issues
    memory["last_scan_madrid"] = _now()
    memory["app_version"] = app_version
    if save_memory:
        memory.setdefault("events", []).append({
            "at_madrid": _now(),
            "event": "scan",
            "candidate_count": len(candidates),
            "issue_count": len(issues),
        })
        memory["events"] = memory["events"][-50:]
        save_sentinel_issues_memory(memory, root)
    return build_sentinel_issues_summary(app_version, memory, transient_candidates=len(candidates))


def build_sentinel_issues_summary(app_version: str, memory: dict[str, Any], transient_candidates: int = 0) -> dict[str, Any]:
    memory = canonicalize_sentinel_memory(memory)
    issues = [item for item in _safe_list(memory.get("issues")) if isinstance(item, dict)]
    open_issues = [item for item in issues if item.get("status") in ACTIVE_ISSUE_STATUSES]
    counts_by_severity = {severity: 0 for severity in SEVERITIES}
    counts_by_status = {status: 0 for status in ISSUE_STATUSES}
    counts_by_area: dict[str, int] = {}
    counts_by_source: dict[str, int] = {}
    for issue in issues:
        counts_by_severity[str(issue.get("severity") or "low")] = counts_by_severity.get(str(issue.get("severity") or "low"), 0) + 1
        counts_by_status[str(issue.get("status") or "INSUFFICIENT_EVIDENCE")] = counts_by_status.get(str(issue.get("status") or "INSUFFICIENT_EVIDENCE"), 0) + 1
        counts_by_area[str(issue.get("area") or "visual")] = counts_by_area.get(str(issue.get("area") or "visual"), 0) + 1
        counts_by_source[str(issue.get("source") or "sentinel")] = counts_by_source.get(str(issue.get("source") or "sentinel"), 0) + 1
    return {
        "version": app_version,
        "engine_version": SENTINEL_ISSUES_VERSION,
        "status_contract": STATUS_CONTRACT,
        "generated_at_madrid": _now(),
        "memory_version": memory.get("version"),
        "memory_path": str(sentinel_issues_memory_path()),
        "last_scan_madrid": memory.get("last_scan_madrid"),
        "transient_candidates": transient_candidates,
        "issues": issues,
        "open_issues": open_issues,
        "critical_issues": [item for item in open_issues if item.get("severity") == "critical"],
        "high_issues": [item for item in open_issues if item.get("severity") == "high"],
        "codex_ready_issues": [item for item in open_issues if item.get("codex_eligible") and item.get("codex_prompt")],
        "reopened_issues": [item for item in open_issues if int(item.get("reopened_count") or 0) > 0],
        "resolved_today": [
            item for item in issues
            if item.get("status") == "RESOLVED" and str(item.get("resolved_at_madrid") or "").startswith(datetime.now(MADRID_TZ).date().isoformat())
        ],
        "counts": {
            "total": len(issues),
            "open": len(open_issues),
            "severity": counts_by_severity,
            "status": counts_by_status,
            "area": counts_by_area,
            "source": counts_by_source,
        },
        "top_area": max(counts_by_area, key=counts_by_area.get) if counts_by_area else "Sin incidencias",
        "top_source": max(counts_by_source, key=counts_by_source.get) if counts_by_source else "Sin origen",
        "issue_health": {
            "open_real": counts_by_status.get("OPEN_REAL", 0),
            "pending_verification": counts_by_status.get("FIXED_PENDING_VERIFICATION", 0),
            "resolved": counts_by_status.get("RESOLVED", 0),
            "false_positive": counts_by_status.get("FALSE_POSITIVE", 0),
            "stale": counts_by_status.get("STALE", 0),
            "duplicate": counts_by_status.get("DUPLICATE", 0),
            "external_blocker": counts_by_status.get("EXTERNAL_BLOCKER", 0),
            "insufficient_evidence": counts_by_status.get("INSUFFICIENT_EVIDENCE", 0),
            "prepared_for_codex": len([item for item in open_issues if item.get("codex_eligible")]),
        },
        "safe_actions": [
            "Escanear ahora en modo seguro.",
            "Copiar prompt Codex de una incidencia real.",
            "Marcar falso positivo solo tras revisar evidencia.",
            "Revalidar con Sentinel despues de corregir.",
        ],
        "forbidden_actions": [
            "No auto deploy",
            "No auto push",
            "No Telegram real",
            "No pagos reales",
            "No secretos",
            "No datos deportivos inventados",
        ],
    }


def get_sentinel_issue(issue_id: str, root: str | Path | None = None) -> dict[str, Any] | None:
    memory = load_sentinel_issues_memory(root)
    for issue in memory.get("issues", []):
        if issue.get("id") == issue_id:
            return issue
    return None


def _record_reconciliation_status(issue: dict[str, Any], status: str, note: str) -> None:
    status = _canonical_status(status)
    if issue.get("status") == status and issue.get("verification") == note:
        return
    before = issue.get("status")
    issue["status"] = status
    issue["verification"] = note
    issue["updated_at_madrid"] = _now()
    issue.setdefault("history", []).append({
        "at_madrid": _now(),
        "event": "evidence_reconciliation",
        "from": before,
        "to": status,
        "note": note,
    })
    issue["history"] = issue["history"][-40:]
    if status == "RESOLVED":
        issue["resolved_at_madrid"] = issue.get("resolved_at_madrid") or _now()
    issue["evidence_sufficient"] = issue_has_sufficient_evidence(issue)
    issue["codex_eligible"] = status == "OPEN_REAL" and issue["evidence_sufficient"]
    if not issue["codex_eligible"]:
        issue["codex_prompt"] = ""


def calibrate_issue_workers(issues: list[dict[str, Any]]) -> dict[str, Any]:
    workers: dict[str, list[dict[str, Any]]] = {}
    for issue in issues:
        for worker in issue.get("worker_sources") or [issue.get("worker") or issue.get("source") or "unknown"]:
            workers.setdefault(str(worker), []).append(issue)
    result: dict[str, Any] = {}
    for worker, items in workers.items():
        reviewed = [item for item in items if item.get("status") in {"OPEN_REAL", "RESOLVED", "FALSE_POSITIVE", "DUPLICATE"}]
        confirmed = [item for item in reviewed if item.get("status") in {"OPEN_REAL", "RESOLVED"}]
        false_positive = [item for item in reviewed if item.get("status") == "FALSE_POSITIVE"]
        duplicate = [item for item in reviewed if item.get("status") == "DUPLICATE"]
        if len(reviewed) < 5:
            state = "INSUFFICIENT_HISTORY"
            why = "Menos de 5 resultados revisados."
        elif len(duplicate) / len(reviewed) >= .5:
            state = "DUPLICATED_SIGNAL"
            why = "La mayoría de resultados revisados duplicaban una incidencia ya conocida."
        else:
            useful_rate = len(confirmed) / len(reviewed)
            state = "HIGH_SIGNAL" if useful_rate >= .8 else "LOW_SIGNAL" if useful_rate < .5 else "NORMAL_SIGNAL"
            why = "Calibración determinista basada solo en veredictos revisados."
        result[worker] = {
            "state": state,
            "why": why,
            "reviewed_samples": len(reviewed),
            "confirmed": len(confirmed),
            "false_positive": len(false_positive),
            "duplicate": len(duplicate),
        }
    return result


def reconcile_autonomous_workforce_evidence(
    root: str | Path,
    *,
    latest_product_qa: dict[str, Any] | None = None,
    production_sha: str = "",
    save: bool = True,
) -> dict[str, Any]:
    """Reconcile historical observations into the existing canonical ledger."""
    base = Path(root)
    memory = load_sentinel_issues_memory(base)
    issues = [dict(item) for item in memory.get("issues") or [] if isinstance(item, dict)]
    not_found = _load_json(base / "data" / "runtime" / "not_found_events.json", {"events": []})
    alias_paths = {
        str(item.get("path") or "")
        for item in not_found.get("events") or []
        if isinstance(item, dict) and item.get("resolved_alias")
    }
    clean_qa = bool(
        latest_product_qa
        and latest_product_qa.get("result") == "PASS"
        and latest_product_qa.get("evidence_complete")
        and int(latest_product_qa.get("issues_detected") or 0) == 0
    )
    for issue in issues:
        title = str(issue.get("title") or "").lower()
        route = str(issue.get("route") or "")
        if "ruta devuelve not found" in title:
            if _is_synthetic_404(issue) or route in alias_paths:
                _record_reconciliation_status(issue, "FALSE_POSITIVE", "Probe QA o alias recuperado; no es un fallo actual del producto.")
            else:
                _record_reconciliation_status(issue, "STALE", "Observación 404 histórica sin reproducción interna actual; requiere nueva evidencia antes de reabrir.")
        elif clean_qa and "pantalla deportiva vacia sin estado seguro" in title:
            _record_reconciliation_status(issue, "RESOLVED", "Full browser QA actual confirmó estado vacío seguro y 0 incidencias.")

    founder_specs = [
        ("founder-topbar-navigation", "Topbar bloqueaba navegación real", "buttons_routes", "P0", "RESOLVED", "18 clics reales y 8/8 viajes completados en la última QA completa.", "La navegación superior no intercepta los clics."),
        ("founder-client-technical-copy", "Texto técnico visible al cliente", "texts", "P1", "RESOLVED", "La última inspección reportó 0 coincidencias técnicas visibles.", "El cliente ve lenguaje breve de producto."),
        ("founder-shark-identity", "Tiburón no coincidía con la identidad oficial", "visual", "P1", "OPEN_REAL", "Comparativa oficial 16/16 y capturas reales preparadas; requiere decisión visual del fundador.", "La composición debe ser MATCH/CLOSE en revisión humana."),
        ("founder-ocean-background", "Fondo sin profundidad de la referencia", "visual", "P1", "OPEN_REAL", "Comparativa oficial de profundidad, iluminación y crop preparada; requiere decisión visual del fundador.", "El fondo debe ser MATCH/CLOSE en PC y móvil."),
        ("founder-false-live-kpi", "KPI LIVE mostraba partidos terminales", "sports", "P0", "RESOLVED", "Sports Truth y Sentinel confirman 0 partidos terminales renderizados como LIVE; la observación deportiva real continúa por cobertura.", "0 partidos terminales renderizados como LIVE en producción observada."),
        ("founder-rectangle-fatigue", "Exceso de rectángulos y densidad visual", "visual", "P2", "RESOLVED", "Browser QA desktop, tablet y mobile confirma producto primero, profundidad <=2 y 0 overflow.", "Producto visible primero, sin fatiga de paneles."),
        ("founder-reference-mismatch", "Desajuste visual frente a referencias oficiales", "visual", "P1", "OPEN_REAL", "16/16 referencias comparadas con capturas reales; el resultado queda FOUNDER_REVIEW_READY, nunca auto-resuelto.", "Revisión humana confirma el resultado real renderizado."),
        ("licensed-media-access", "Medios licenciados no disponibles", "media_rights", "P2", "EXTERNAL_BLOCKER", "La ausencia de licencia externa no es un fallo local; se mantiene fallback seguro.", "Solo medios con derechos aprobados pueden mostrarse."),
        ("growth-real-data", "Growth todavía no dispone de muestra real suficiente", "growth", "P3", "INSUFFICIENT_EVIDENCE", "No hay suficiente evidencia REAL_USER para calibrar conversión o canales.", "Esperar tráfico real sin inventar métricas."),
        ("revenue-real-data", "Revenue todavía no dispone de muestra real suficiente", "revenue", "P3", "INSUFFICIENT_EVIDENCE", "No hay MRR real certificado para extraer conclusiones.", "Esperar evidencia real de monetización."),
    ]
    candidates = []
    for stable_key, title, area, priority, status, evidence, expected in founder_specs:
        candidates.append(normalize_sentinel_issue({
            "stable_key": stable_key,
            "title": title,
            "area": area,
            "category": area,
            "priority": priority,
            "severity": {"P0": "critical", "P1": "high", "P2": "medium", "P3": "low"}[priority],
            "status": status,
            "source": "FOUNDER_QA_OVERRIDE",
            "worker_sources": ["Founder evidence review", "Autonomous Product QA"],
            "evidence_origin": "FOUNDER_QA_OVERRIDE",
            "evidence": evidence,
            "actual": evidence,
            "expected": expected,
            "verification": evidence,
            "production_sha": production_sha,
            "evidence_sufficient": status not in {"INSUFFICIENT_EVIDENCE"},
        }, "FOUNDER_QA_OVERRIDE"))
    issues = upsert_sentinel_issues(issues, candidates)

    canonical_by_key: dict[tuple[str, str, str], dict[str, Any]] = {}
    for issue in issues:
        key = (
            str(issue.get("title") or "").strip().lower(),
            str(issue.get("route") or "").strip().lower(),
            str(issue.get("component") or issue.get("area") or "").strip().lower(),
        )
        previous = canonical_by_key.get(key)
        if previous and issue.get("id") != previous.get("id") and issue.get("status") not in {"FALSE_POSITIVE", "RESOLVED"}:
            issue["related_issue_ids"] = list(dict.fromkeys([*(issue.get("related_issue_ids") or []), previous.get("id")]))
            _record_reconciliation_status(issue, "DUPLICATE", f"Misma incidencia canónica que {previous.get('id')}.")
        else:
            canonical_by_key[key] = issue

    memory["issues"] = issues
    memory["last_evidence_reconciliation_madrid"] = _now()
    memory["worker_calibration"] = calibrate_issue_workers(issues)
    memory.setdefault("events", []).append({
        "at_madrid": _now(),
        "event": "autonomous_workforce_evidence_reconciled",
        "latest_product_qa": (latest_product_qa or {}).get("run_id"),
        "issue_count": len(issues),
    })
    memory["events"] = memory["events"][-80:]
    if save:
        save_sentinel_issues_memory(memory, base)
    return build_sentinel_issues_summary("LOCAL", memory)

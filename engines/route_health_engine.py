"""Route health and modularization helpers for NeMeSiS SHARK PRO.

This module is intentionally read-only. It does not move routes or mutate app
state; it gives the admin a safe map of the current Flask surface before future
blueprint extraction work.
"""
from __future__ import annotations

import inspect
import re
from collections import Counter, defaultdict
from typing import Any


def _safe_str(value: Any) -> str:
    return str(value or "").strip()


def _bucket_for_rule(rule: str, methods: list[str]) -> str:
    path = _safe_str(rule)
    method_set = {m.upper() for m in methods or []}
    if path.startswith("/static/") or path in {"/service-worker.js", "/manifest.json", "/favicon.ico"}:
        return "static"
    if path.startswith("/api/automation/"):
        return "cron"
    if path.startswith("/api/admin/"):
        return "admin_api"
    if path.startswith("/api/"):
        return "api"
    if path.startswith("/admin"):
        return "admin"
    if "POST" in method_set and any(token in path for token in ("login", "registro", "password", "reset")):
        return "auth"
    if path in {"/", "/login", "/cliente-login", "/registro", "/privacy", "/terms", "/contact", "/responsible-gaming"}:
        return "public"
    if path.startswith("/telegram"):
        return "telegram"
    return "client"


def _route_risk(rule: str, endpoint: str, methods: list[str], source: str) -> dict:
    path = _safe_str(rule)
    method_set = {m.upper() for m in methods or []}
    source = source or ""
    issues: list[str] = []
    severity = "OK"

    if path.startswith("/admin") and "is_admin_session" not in source and "admin_json_forbidden" not in source:
        issues.append("Ruta admin sin comprobación admin visible en la función.")
        severity = "WARN"
    if path.startswith("/api/admin") and "admin_json_forbidden" not in source and "is_admin_session" not in source:
        issues.append("API admin sin protección admin visible.")
        severity = "WARN"
    if path.startswith("/api/automation") and "automation_cron_access_allowed" not in source and "automation_secret" not in source:
        issues.append("Endpoint Cron sin validación de secret visible.")
        severity = "WARN"
    if method_set & {"POST", "PUT", "PATCH", "DELETE"} and not path.startswith("/api/automation") and path not in {"/telegram/webhook"}:
        if "csrf" not in source.lower() and "admin_json_forbidden" not in source and "is_admin_session" not in source:
            issues.append("Método sensible; confirmar CSRF/rate limit global.")
            severity = "INFO" if severity == "OK" else severity
    if "debug" in path.lower() or "raw" in path.lower():
        issues.append("Ruta con nombre técnico; comprobar que no sea visible al cliente.")
        severity = "INFO" if severity == "OK" else severity

    return {"severity": severity, "issues": issues}


def _blueprint_target(bucket: str) -> str:
    return {
        "admin": "blueprints/admin.py",
        "admin_api": "blueprints/admin_api.py",
        "api": "blueprints/api.py",
        "auth": "blueprints/auth.py",
        "client": "blueprints/client.py",
        "cron": "blueprints/cron.py",
        "public": "blueprints/public.py",
        "telegram": "blueprints/telegram.py",
        "static": "static/service handlers",
    }.get(bucket, "blueprints/client.py")


def route_health_snapshot(app: Any) -> dict:
    """Return a safe, serializable route health snapshot for admin use."""
    routes = []
    bucket_counts: Counter[str] = Counter()
    method_counts: Counter[str] = Counter()
    template_hits: Counter[str] = Counter()
    warnings = []
    blueprint_targets: defaultdict[str, int] = defaultdict(int)

    url_map = getattr(app, "url_map", None)
    rules = sorted(getattr(url_map, "iter_rules", lambda: [])(), key=lambda r: str(getattr(r, "rule", "")))
    for rule_obj in rules:
        rule = str(getattr(rule_obj, "rule", ""))
        endpoint = str(getattr(rule_obj, "endpoint", ""))
        methods = sorted(m for m in getattr(rule_obj, "methods", set()) if m not in {"HEAD", "OPTIONS"})
        view = getattr(app, "view_functions", {}).get(endpoint)
        source = ""
        try:
            source = inspect.getsource(view) if view else ""
        except Exception:
            source = ""
        bucket = _bucket_for_rule(rule, methods)
        bucket_counts[bucket] += 1
        for method in methods:
            method_counts[method] += 1
        target = _blueprint_target(bucket)
        blueprint_targets[target] += 1
        risk = _route_risk(rule, endpoint, methods, source)
        template_match = re.search(r"render_template\(\s*[\"']([^\"']+)[\"']", source)
        template = template_match.group(1) if template_match else ""
        if template:
            template_hits[template] += 1
        if risk["issues"]:
            warnings.append({"rule": rule, "endpoint": endpoint, "severity": risk["severity"], "issues": risk["issues"]})
        routes.append({
            "rule": rule,
            "endpoint": endpoint,
            "methods": methods,
            "bucket": bucket,
            "blueprint_target": target,
            "template": template,
            "severity": risk["severity"],
            "issues": risk["issues"],
        })

    total = len(routes)
    admin_count = bucket_counts.get("admin", 0) + bucket_counts.get("admin_api", 0)
    api_count = bucket_counts.get("api", 0) + bucket_counts.get("admin_api", 0) + bucket_counts.get("cron", 0)
    risk_count = sum(1 for item in routes if item["severity"] in {"WARN", "ERROR"})
    recommended_next_steps = [
        "No mover rutas de golpe: extraer primero APIs admin o páginas admin pequeñas.",
        "Mantener app.py funcional como fuente estable hasta que cada blueprint tenga smoke propio.",
        "Añadir tests por grupo antes de migrar rutas críticas como login, Cron y Telegram.",
        "Usar este mapa para elegir lotes de 10-20 rutas, no todo el monolito a la vez.",
    ]
    if total >= 180:
        recommended_next_steps.insert(0, "app.py sigue muy grande: preparar migración gradual a blueprints por grupos.")
    if risk_count:
        recommended_next_steps.insert(0, "Revisar avisos de protección antes de publicar nuevas rutas.")

    return {
        "ok": True,
        "total_routes": total,
        "admin_routes": admin_count,
        "api_routes": api_count,
        "client_routes": bucket_counts.get("client", 0),
        "public_routes": bucket_counts.get("public", 0),
        "cron_routes": bucket_counts.get("cron", 0),
        "telegram_routes": bucket_counts.get("telegram", 0),
        "warnings_count": risk_count,
        "bucket_counts": dict(sorted(bucket_counts.items())),
        "method_counts": dict(sorted(method_counts.items())),
        "blueprint_targets": dict(sorted(blueprint_targets.items())),
        "top_templates": [{"template": name, "uses": count} for name, count in template_hits.most_common(12)],
        "warnings": warnings[:50],
        "routes": routes,
        "recommended_next_steps": recommended_next_steps,
        "note": "Mapa de rutas solo lectura. No modifica rutas ni mueve archivos.",
    }

"""V606 - Blueprint Migration Phase 1

Non-invasive architecture audit utilities for NeMeSiS SHARK PRO.
This module does not modify Flask routes by itself. It helps map and group
existing app.py routes so the project can be migrated to Blueprints safely.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from pathlib import Path
import ast
import re
from typing import Dict, List, Any


@dataclass
class RouteInfo:
    rule: str
    endpoint: str
    methods: List[str]
    line: int
    group: str


def guess_route_group(rule: str, endpoint: str = "") -> str:
    text = f"{rule} {endpoint}".lower()
    if any(k in text for k in ["admin", "beta", "data-center", "audit"]):
        return "admin"
    if any(k in text for k in ["login", "registro", "logout", "account", "perfil", "password", "auth"]):
        return "auth"
    if any(k in text for k in ["telegram", "webhook"]):
        return "telegram"
    if any(k in text for k in ["pick", "recommendation", "autopilot", "shark", "odds", "value"]):
        return "shark_picks"
    if any(k in text for k in ["live", "match", "calendar", "result", "fixture", "standings"]):
        return "football"
    if any(k in text for k in ["api", "health", "version", "storage", "db-check"]):
        return "api_system"
    return "main"


def parse_app_routes(app_py: str | Path = "app.py") -> List[RouteInfo]:
    path = Path(app_py)
    if not path.exists():
        return []
    source = path.read_text(encoding="utf-8", errors="ignore")
    tree = ast.parse(source)
    routes: List[RouteInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            fn = deco.func
            is_route = (
                isinstance(fn, ast.Attribute) and fn.attr == "route"
            )
            if not is_route or not deco.args:
                continue
            rule = ""
            if isinstance(deco.args[0], ast.Constant):
                rule = str(deco.args[0].value)
            methods = ["GET"]
            for kw in deco.keywords:
                if kw.arg == "methods" and isinstance(kw.value, (ast.List, ast.Tuple)):
                    methods = [str(x.value) for x in kw.value.elts if isinstance(x, ast.Constant)] or methods
            routes.append(RouteInfo(
                rule=rule,
                endpoint=node.name,
                methods=methods,
                line=getattr(node, "lineno", 0),
                group=guess_route_group(rule, node.name),
            ))
    return sorted(routes, key=lambda r: (r.group, r.rule, r.line))


def build_route_summary(app_py: str | Path = "app.py") -> Dict[str, Any]:
    routes = parse_app_routes(app_py)
    groups: Dict[str, List[Dict[str, Any]]] = {}
    duplicates: Dict[str, int] = {}
    for route in routes:
        groups.setdefault(route.group, []).append(asdict(route))
        duplicates[route.rule] = duplicates.get(route.rule, 0) + 1
    duplicated_rules = {k: v for k, v in duplicates.items() if v > 1}
    return {
        "ok": True,
        "total_routes": len(routes),
        "groups": {k: len(v) for k, v in groups.items()},
        "duplicated_rules": duplicated_rules,
        "routes": [asdict(r) for r in routes],
        "migration_priority": ["auth", "telegram", "api_system", "football", "shark_picks", "admin", "main"],
        "recommendation": "Migrar primero auth y telegram porque son flujos críticos pero acotados.",
    }


def write_route_map(output_path: str | Path = "ROUTE_MAP_V606.md", app_py: str | Path = "app.py") -> Path:
    summary = build_route_summary(app_py)
    out = Path(output_path)
    lines = ["# V606 — Route Map & Blueprint Migration Plan", ""]
    lines.append(f"Total de rutas detectadas: {summary['total_routes']}")
    lines.append("")
    lines.append("## Rutas por grupo")
    for group, count in summary["groups"].items():
        lines.append(f"- {group}: {count}")
    lines.append("")
    lines.append("## Duplicadas")
    if summary["duplicated_rules"]:
        for rule, count in summary["duplicated_rules"].items():
            lines.append(f"- {rule}: {count}")
    else:
        lines.append("No se detectaron rutas duplicadas por regla.")
    lines.append("")
    lines.append("## Detalle")
    for r in summary["routes"]:
        lines.append(f"- `{r['rule']}` → `{r['endpoint']}` · {','.join(r['methods'])} · línea {r['line']} · grupo `{r['group']}`")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


# ---------------------------------------------------------------------------
# V608 - runtime architecture scoring and migration plan
# ---------------------------------------------------------------------------

def runtime_url_map(app) -> List[Dict[str, Any]]:
    """Return a safe runtime inventory from Flask's url_map."""
    routes: List[Dict[str, Any]] = []
    try:
        rules = sorted(app.url_map.iter_rules(), key=lambda r: (r.rule, r.endpoint))
    except Exception:
        return routes
    for rule in rules:
        methods = sorted(m for m in getattr(rule, "methods", set()) if m not in {"HEAD", "OPTIONS"}) or ["GET"]
        routes.append({
            "rule": rule.rule,
            "endpoint": rule.endpoint,
            "methods": methods,
            "blueprint": rule.endpoint.split(".")[0] if "." in rule.endpoint else "legacy_app",
            "group": guess_route_group(rule.rule, rule.endpoint),
        })
    return routes


def blueprint_runtime_summary(app) -> Dict[str, Any]:
    routes = runtime_url_map(app)
    by_blueprint: Dict[str, int] = {}
    by_group: Dict[str, int] = {}
    duplicated: Dict[str, int] = {}
    for route in routes:
        by_blueprint[route["blueprint"]] = by_blueprint.get(route["blueprint"], 0) + 1
        by_group[route["group"]] = by_group.get(route["group"], 0) + 1
        duplicated[route["rule"]] = duplicated.get(route["rule"], 0) + 1
    return {
        "total_routes": len(routes),
        "by_blueprint": dict(sorted(by_blueprint.items(), key=lambda x: (-x[1], x[0]))),
        "by_group": dict(sorted(by_group.items(), key=lambda x: (-x[1], x[0]))),
        "duplicated_rules": {k: v for k, v in duplicated.items() if v > 1},
        "routes": routes,
    }


def architecture_quality_score(runtime_summary: Dict[str, Any], app_py: str | Path = "app.py") -> Dict[str, Any]:
    app_path = Path(app_py)
    try:
        lines = len(app_path.read_text(encoding="utf-8", errors="ignore").splitlines())
    except Exception:
        lines = 0
    total_routes = int(runtime_summary.get("total_routes") or 0)
    legacy_routes = int(runtime_summary.get("by_blueprint", {}).get("legacy_app", 0))
    blueprint_routes = max(total_routes - legacy_routes, 0)
    duplicated = len(runtime_summary.get("duplicated_rules", {}) or {})

    # Conservative score: rewards having blueprints and clean routes, penalizes giant app.py.
    score = 100
    if lines > 9000:
        score -= 22
    elif lines > 6000:
        score -= 16
    elif lines > 3000:
        score -= 8
    if total_routes > 240:
        score -= 14
    elif total_routes > 160:
        score -= 8
    if legacy_routes > 180:
        score -= 12
    elif legacy_routes > 100:
        score -= 7
    if duplicated:
        score -= min(duplicated * 4, 16)
    if blueprint_routes:
        score += min(blueprint_routes * 2, 8)
    score = max(0, min(100, score))

    status = "crítico" if score < 50 else "mejorable" if score < 75 else "sólido" if score < 90 else "excelente"
    return {
        "score": score,
        "status": status,
        "app_py_lines": lines,
        "total_routes": total_routes,
        "legacy_routes": legacy_routes,
        "blueprint_routes": blueprint_routes,
        "duplicated_route_count": duplicated,
    }


def migration_batches(runtime_summary: Dict[str, Any]) -> List[Dict[str, Any]]:
    groups = runtime_summary.get("by_group", {}) or {}
    order = [
        ("auth", "Autenticación y cuentas", "Rutas de login, registro, perfil y sesión."),
        ("telegram", "Telegram", "Webhook, cola, auditoría y entregas."),
        ("api_system", "APIs de sistema", "Health, versionado, storage y diagnósticos."),
        ("football", "Fútbol y live", "Calendario, partidos, resultados, live y match detail."),
        ("shark_picks", "SHARK y picks", "Pronósticos, value, learning, accuracy y auto picks."),
        ("admin", "Admin", "Data Center, beta, observabilidad y gestión."),
        ("main", "Landing y páginas generales", "Inicio, páginas públicas y enlaces."),
    ]
    batches: List[Dict[str, Any]] = []
    for idx, (group, title, description) in enumerate(order, start=1):
        count = int(groups.get(group, 0) or 0)
        batches.append({
            "phase": idx,
            "group": group,
            "title": title,
            "description": description,
            "routes": count,
            "priority": "alta" if group in {"auth", "telegram", "api_system"} else "media",
            "risk": "medio" if group in {"auth", "telegram"} else "bajo" if group == "api_system" else "medio-alto",
        })
    return batches


def build_runtime_architecture_summary(app, app_py: str | Path = "app.py") -> Dict[str, Any]:
    runtime = blueprint_runtime_summary(app)
    score = architecture_quality_score(runtime, app_py=app_py)
    return {
        "ok": True,
        "runtime": runtime,
        "quality": score,
        "migration_batches": migration_batches(runtime),
        "next_recommendation": "Migrar auth y telegram en fases pequeñas, manteniendo URLs actuales y tests de humo antes de cada deploy.",
        "safety_rule": "No eliminar rutas legacy hasta que el blueprint equivalente tenga test y tráfico verificado.",
    }

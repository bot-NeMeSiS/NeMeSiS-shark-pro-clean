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

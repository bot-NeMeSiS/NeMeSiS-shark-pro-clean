"""Read-only navigation integrity audit for NeMeSiS SHARK PRO.

The engine compares literal UI destinations with Flask's registered URL map.
It never calls external providers and never mutates production data.
"""
from __future__ import annotations

import ast
import html
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from werkzeug.exceptions import MethodNotAllowed, NotFound
from werkzeug.routing import BuildError, RequestRedirect


BROKEN_RESULTS = {
    "ROTA_404",
    "ROTA_500",
    "ENDPOINT_INEXISTENTE",
    "PARÁMETRO_OBLIGATORIO_FALTANTE",
    "LOOP_REDIRECT",
    "BOTÓN_SIN_ACCIÓN",
    "TEMPLATE_HUÉRFANO",
}

SAFE_RESULTS = {
    "OK",
    "REDIRECT_SEGURO",
    "REQUIERE_SESIÓN_CLIENTE",
    "REQUIERE_SESIÓN_ADMIN",
    "RUTA_INTERNA_NO_DEBE_SER_VISIBLE",
}

CLIENT_AUTH_PREFIXES = (
    "/app",
    "/profile",
    "/perfil",
    "/telegram",
    "/favorites",
    "/favoritos",
    "/memberships",
)

EXTERNAL_SCHEMES = ("http://", "https://", "mailto:", "tel:", "data:", "blob:")
SKIP_TEMPLATE_PREFIXES = ("partials/", "components/")


def _now_madrid() -> str:
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Europe/Madrid")).replace(microsecond=0).isoformat()
    except Exception:
        return datetime.now().replace(microsecond=0).isoformat()


def _safe_text(value: Any, limit: int = 500) -> str:
    text = str(value or "").replace("\r", " ").replace("\n", " ").strip()
    lowered = text.lower()
    for token in ("secret=", "token=", "api_key=", "apikey=", "password="):
        index = lowered.find(token)
        if index >= 0:
            text = text[: index + len(token)] + "[redacted]"
            break
    return text[:limit]


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, max(0, offset)) + 1


def _visible_text(fragment: str) -> str:
    fragment = re.sub(r"<[^>]+>", " ", fragment or "")
    fragment = re.sub(r"\{[{%].*?[}%]\}", " ", fragment, flags=re.DOTALL)
    return _safe_text(html.unescape(re.sub(r"\s+", " ", fragment)), 180)


def _attribute_map(source: str) -> dict[str, str]:
    attrs: dict[str, str] = {}
    for name, quote, value in re.findall(r"([:\w-]+)\s*=\s*(['\"])(.*?)\2", source or "", re.DOTALL):
        attrs[name.lower()] = _safe_text(value, 500)
    return attrs


@dataclass
class NavigationEntry:
    origin_screen: str
    visible_text: str
    selector: str
    generated_url: str
    flask_endpoint: str
    methods: list[str]
    authentication: str
    expected_status: str
    obtained_status: str
    result: str
    correction: str
    source_kind: str
    line: int
    detail: str = ""

    def payload(self) -> dict[str, Any]:
        return asdict(self)


class _NavigationHTMLParser(HTMLParser):
    def __init__(self, origin: str):
        super().__init__(convert_charrefs=True)
        self.origin = origin
        self.entries: list[dict[str, Any]] = []
        self.form_depth = 0
        self._capture: list[dict[str, Any]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = {str(k).lower(): str(v or "") for k, v in attrs}
        line = self.getpos()[0]
        if tag == "form":
            self.form_depth += 1
            action = attr.get("action", "")
            if action:
                self.entries.append({
                    "kind": "form",
                    "target": action,
                    "text": attr.get("aria-label") or "Formulario",
                    "selector": f"form[action={action}]",
                    "method": (attr.get("method") or "GET").upper(),
                    "line": line,
                })
        elif tag == "a":
            target = attr.get("href", "")
            record = {
                "kind": "link" if target else "static_anchor",
                "target": target,
                "text": attr.get("aria-label") or attr.get("title") or "",
                "selector": f"a[href={target}]" if target else "a:not([href])",
                "method": "GET",
                "line": line,
            }
            self.entries.append(record)
            self._capture.append({"tag": "a", "index": len(self.entries) - 1, "parts": []})
        elif tag == "button":
            has_action = any(
                key in attr
                for key in (
                    "onclick", "data-url", "data-href", "data-action", "data-q",
                    "formaction", "form",
                )
            )
            button_type = (attr.get("type") or "submit").lower()
            if self.form_depth <= 0 and not has_action and button_type != "reset":
                record = {
                    "kind": "button",
                    "target": "",
                    "text": attr.get("aria-label") or attr.get("title") or "",
                    "selector": "button" + (f"#{attr['id']}" if attr.get("id") else ""),
                    "method": "POST" if button_type == "submit" else "GET",
                    "line": line,
                    "has_identifier": bool(attr.get("id") or attr.get("class")),
                }
                self.entries.append(record)
                self._capture.append({"tag": "button", "index": len(self.entries) - 1, "parts": []})

    def handle_data(self, data: str) -> None:
        if self._capture:
            self._capture[-1]["parts"].append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "form":
            self.form_depth = max(0, self.form_depth - 1)
        if self._capture and self._capture[-1]["tag"] == tag:
            capture = self._capture.pop()
            text = _safe_text(" ".join(capture["parts"]), 180)
            if text:
                self.entries[capture["index"]]["text"] = text


def _route_authentication(path: str) -> str:
    if path.startswith("/api/admin/") or path.startswith("/admin"):
        return "admin"
    if path.startswith(CLIENT_AUTH_PREFIXES):
        return "client"
    return "public"


def _route_result_for_auth(path: str) -> str:
    auth = _route_authentication(path)
    if auth == "admin":
        return "REQUIERE_SESIÓN_ADMIN"
    if auth == "client":
        return "REQUIERE_SESIÓN_CLIENTE"
    return "OK"


def _endpoint_methods(app: Any, endpoint: str) -> list[str]:
    methods: set[str] = set()
    for rule in app.url_map.iter_rules(endpoint):
        methods.update(method for method in rule.methods if method not in {"HEAD", "OPTIONS"})
    return sorted(methods)


def _resolve_url_for_target(app: Any, raw: str) -> tuple[str, str, str]:
    match = re.search(r"url_for\(\s*['\"]([^'\"]+)['\"]", raw or "")
    if not match:
        return "", "", ""
    endpoint = match.group(1)
    if endpoint not in app.view_functions:
        return endpoint, "ENDPOINT_INEXISTENTE", "El endpoint usado por url_for no está registrado."
    return endpoint, "OK", "Endpoint url_for registrado."


def resolve_safe_internal_route(
    app: Any,
    *,
    endpoint: str = "",
    values: dict[str, Any] | None = None,
    path: str = "",
    fallback: str = "/calendar",
) -> dict[str, Any]:
    """Resolve a route without raising BuildError or accepting external URLs."""
    fallback = fallback if str(fallback).startswith("/") else "/calendar"
    adapter = app.url_map.bind("localhost")
    if endpoint:
        if endpoint not in app.view_functions:
            return {"ok": False, "url": fallback, "status": "ENDPOINT_MISSING", "reason": "endpoint_missing"}
        try:
            url = adapter.build(endpoint, values or {}, force_external=False)
            return {"ok": True, "url": url, "status": "OK", "reason": "endpoint_resolved"}
        except BuildError:
            return {"ok": False, "url": fallback, "status": "PARAMETER_MISSING", "reason": "required_parameter_missing"}
    raw_path = _safe_text(path, 500)
    if not raw_path.startswith("/") or raw_path.startswith("//"):
        return {"ok": False, "url": fallback, "status": "UNSAFE", "reason": "external_or_relative_target"}
    clean = urlsplit(raw_path).path or "/"
    try:
        endpoint_name, _values = adapter.match(clean, method="GET")
        return {"ok": True, "url": raw_path, "status": "OK", "endpoint": endpoint_name, "reason": "path_resolved"}
    except RequestRedirect as exc:
        return {"ok": True, "url": exc.new_url, "status": "REDIRECT", "reason": "canonical_redirect"}
    except MethodNotAllowed:
        return {"ok": False, "url": fallback, "status": "METHOD_MISMATCH", "reason": "method_not_allowed"}
    except NotFound:
        return {"ok": False, "url": fallback, "status": "NOT_FOUND", "reason": "path_not_registered"}


def _classify_target(app: Any, target: str, method: str, aliases: dict[str, str]) -> tuple[str, str, str, list[str]]:
    target = _safe_text(target, 500)
    method = (method or "GET").upper()
    if not target:
        return "BOTÓN_SIN_ACCIÓN", "", "Destino vacío.", []
    lowered = target.lower()
    if lowered.startswith(EXTERNAL_SCHEMES):
        return "OK", "external", "Destino externo explícito.", [method]
    if target.startswith("#"):
        return "OK", "fragment", "Ancla dentro de la misma pantalla.", [method]
    if lowered.startswith("javascript:void"):
        return "BOTÓN_SIN_ACCIÓN", "", "javascript:void no define una acción real.", [method]
    if "url_for(" in target:
        endpoint, result, detail = _resolve_url_for_target(app, target)
        return result, endpoint, detail, _endpoint_methods(app, endpoint) if endpoint in app.view_functions else []
    if "{{" in target or "{%" in target:
        return "WARNING", "dynamic_template", "Destino dinámico; se valida al renderizar y en Browser QA.", [method]
    if not target.startswith("/"):
        return "ROTA_404", "", "URL relativa ambigua; debe ser interna absoluta o externa explícita.", [method]
    clean = urlsplit(target).path or "/"
    adapter = app.url_map.bind("localhost")
    try:
        endpoint, _values = adapter.match(clean, method=method)
        return _route_result_for_auth(clean), endpoint, "Ruta registrada.", _endpoint_methods(app, endpoint)
    except RequestRedirect as exc:
        return "REDIRECT_SEGURO", "", f"Redirección canónica a {exc.new_url}.", [method]
    except MethodNotAllowed:
        try:
            endpoint, _values = adapter.match(clean, method="GET" if method != "GET" else "POST")
            return "ENDPOINT_INEXISTENTE", endpoint, f"La ruta existe pero no acepta {method}.", _endpoint_methods(app, endpoint)
        except Exception:
            return "ENDPOINT_INEXISTENTE", "", f"No hay endpoint compatible con {method}.", [method]
    except NotFound:
        if clean.rstrip("/") in aliases:
            return "REDIRECT_SEGURO", "legacy_alias", f"Alias compatible hacia {aliases[clean.rstrip('/')]}", [method]
        dynamic_prefix = any(
            "<" in rule.rule and clean.startswith(rule.rule.split("<", 1)[0])
            for rule in app.url_map.iter_rules()
        )
        if dynamic_prefix and ("{{" in target or "<" in target):
            return "PARÁMETRO_OBLIGATORIO_FALTANTE", "", "Ruta dinámica sin parámetro resoluble.", [method]
        return "ROTA_404", "", "No existe una ruta Flask para este destino.", [method]


def _template_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for path in sorted((root / "templates").rglob("*.html")):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        origin = path.relative_to(root).as_posix()
        parser = _NavigationHTMLParser(origin)
        try:
            parser.feed(text)
        except Exception:
            pass
        entries.extend({"origin": origin, **item} for item in parser.entries)
        for match in re.finditer(
            r"(?:window\.)?location(?:\.href)?\s*=\s*(['\"])(/[^'\"]*)\1|fetch\(\s*(['\"])(/[^'\"]*)\3|data-(?:url|href)\s*=\s*(['\"])(/[^'\"]*)\5",
            text,
            flags=re.IGNORECASE,
        ):
            target = next((group for group in (match.group(2), match.group(4), match.group(6)) if group), "")
            tail = text[match.end():match.end() + 260]
            method = "POST" if match.group(4) and re.search(
                r"method\s*:\s*['\"]POST['\"]", tail, re.IGNORECASE
            ) else "GET"
            if match.group(4) and re.match(r"\s*\+", tail):
                target += "{{dynamic}}"
            entries.append({
                "origin": origin,
                "kind": "javascript_or_data_url",
                "target": target,
                "text": "Acción JavaScript",
                "selector": "script/data-url",
                "method": method,
                "line": _line_for_offset(text, match.start()),
            })
    return entries


def _source_route_entries(root: Path) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for relative in ("app.py",):
        path = root / relative
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for match in re.finditer(r"redirect\(\s*(['\"])(/[^'\"]*)\1", text):
            entries.append({
                "origin": relative,
                "kind": "redirect",
                "target": match.group(2),
                "text": "redirect",
                "selector": "redirect()",
                "method": "GET",
                "line": _line_for_offset(text, match.start()),
            })
        for match in re.finditer(r"url_for\(\s*(['\"])([^'\"]+)\1", text):
            entries.append({
                "origin": relative,
                "kind": "url_for",
                "target": f"url_for('{match.group(2)}')",
                "text": match.group(2),
                "selector": "url_for()",
                "method": "GET",
                "line": _line_for_offset(text, match.start()),
            })
    return entries


def _orphan_templates(root: Path) -> list[str]:
    app_text = (root / "app.py").read_text(encoding="utf-8-sig", errors="replace")
    referenced = set(re.findall(r"render_template\(\s*['\"]([^'\"]+)['\"]", app_text))
    for path in (root / "templates").rglob("*.html"):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        referenced.update(re.findall(r"(?:extends|include|import|from)\s+['\"]([^'\"]+)['\"]", text))
    return sorted(
        path.relative_to(root / "templates").as_posix()
        for path in (root / "templates").rglob("*.html")
        if path.relative_to(root / "templates").as_posix() not in referenced
        and not path.relative_to(root / "templates").as_posix().startswith(SKIP_TEMPLATE_PREFIXES)
    )


def _entry_payload(app: Any, item: dict[str, Any], aliases: dict[str, str]) -> dict[str, Any]:
    target = item.get("target") or ""
    result, endpoint, detail, methods = _classify_target(app, target, item.get("method") or "GET", aliases)
    if item.get("kind") == "static_anchor" and not target:
        result = "RUTA_INTERNA_NO_DEBE_SER_VISIBLE"
        detail = "Elemento de metrica no interactivo; no genera navegacion."
    if item.get("kind") == "button" and not target:
        if item.get("has_identifier"):
            result = "WARNING"
            detail = "Botón sin URL literal; tiene identificador para acción JavaScript y requiere Browser QA."
        else:
            result = "BOTÓN_SIN_ACCIÓN"
            detail = "Botón fuera de formulario sin destino ni acción identificable."
    auth = _route_authentication(urlsplit(target).path if str(target).startswith("/") else "")
    expected = "200/redirect seguro"
    if auth == "admin":
        expected = "200 admin o 302/403 sin sesión"
    elif auth == "client":
        expected = "200 cliente o 302/403 sin sesión"
    return NavigationEntry(
        origin_screen=item.get("origin") or "",
        visible_text=item.get("text") or item.get("kind") or "",
        selector=item.get("selector") or "",
        generated_url=target,
        flask_endpoint=endpoint,
        methods=methods or [item.get("method") or "GET"],
        authentication=auth,
        expected_status=expected,
        obtained_status="static_route_map",
        result=result,
        correction="" if result not in BROKEN_RESULTS else "Corregir destino o deshabilitar con explicación.",
        source_kind=item.get("kind") or "",
        line=int(item.get("line") or 0),
        detail=detail,
    ).payload()


def _follow_redirects_safely(client: Any, path: str, limit: int = 8) -> dict[str, Any]:
    visited: list[str] = []
    current = path
    response = None
    for _index in range(limit):
        if current in visited:
            return {"path": path, "status": 508, "result": "LOOP_REDIRECT", "chain": visited + [current]}
        visited.append(current)
        response = client.get(current, follow_redirects=False)
        if response.status_code not in {301, 302, 303, 307, 308}:
            break
        location = response.headers.get("Location", "")
        if not location or location.startswith(("http://", "https://", "//")):
            break
        current = urlsplit(location).path or "/"
        if urlsplit(location).query:
            current += "?" + urlsplit(location).query
    if response is None:
        return {"path": path, "status": 0, "result": "BROKEN", "chain": visited}
    status = int(response.status_code)
    if status >= 500:
        result = "ROTA_500"
    elif status == 404:
        result = "ROTA_404"
    elif status in {401, 403}:
        result = "REDIRECT_SEGURO"
    else:
        result = "OK"
    return {
        "path": path,
        "status": status,
        "result": result,
        "chain": visited,
        "final_path": current,
        "location": response.headers.get("Location", ""),
        "content_type": response.headers.get("Content-Type", ""),
    }


def smoke_navigation(app: Any) -> dict[str, Any]:
    public_paths = [
        "/", "/cliente-login", "/login", "/entrar", "/registro", "/support",
        "/terms", "/privacy", "/refunds", "/membresias", "/clientes",
    ]
    client_paths = [
        "/app", "/calendar", "/calendario", "/partidos", "/partidos-hoy",
        "/live", "/directo", "/picks", "/track-record", "/historico",
        "/shark", "/telegram", "/profile", "/memberships", "/favoritos",
    ]
    admin_paths = [
        "/admin/dashboard", "/admin/users", "/admin/memberships", "/admin/payments",
        "/admin/picks", "/admin/matches", "/admin/data-center",
        "/admin/telegram/command-center", "/admin/automation-workforce",
        "/admin/daily-automation", "/admin/autonomous-company-sentinel",
        "/admin/sentinel-issues", "/admin/sentinel-codex-outbox",
        "/admin/not-found-events", "/admin/launch-certification",
        "/admin/final-certification", "/admin/settings", "/admin/navigation-integrity",
    ]
    client = app.test_client()
    public = [_follow_redirects_safely(client, path) for path in public_paths]
    client = app.test_client()
    with client.session_transaction() as sess:
        sess.update({
            "user_id": "v929-client-mock",
            "user_name": "Cliente QA",
            "username": "cliente_qa",
            "user_email": "qa-client@example.invalid",
            "user_role": "PRO",
            "user_membership": "PRO",
            "membership": "PRO",
        })
    client_results = [_follow_redirects_safely(client, path) for path in client_paths]
    admin = app.test_client()
    with admin.session_transaction() as sess:
        sess.update({
            "user_id": "v929-admin-mock",
            "user_name": "Admin QA",
            "username": "admin_qa",
            "user_email": "qa-admin@example.invalid",
            "user_role": "ADMIN",
            "user_membership": "ADMIN",
            "membership": "ADMIN",
        })
    admin_results = [_follow_redirects_safely(admin, path) for path in admin_paths]
    dynamic = [
        _follow_redirects_safely(client, "/match/v929-id-inexistente"),
        _follow_redirects_safely(client, "/team/v929-id-inexistente"),
        _follow_redirects_safely(client, "/highlight/v929-id-inexistente"),
    ]
    all_items = public + client_results + admin_results + dynamic
    return {
        "public": public,
        "client_mock": client_results,
        "admin_mock": admin_results,
        "dynamic_missing": dynamic,
        "tested": len(all_items),
        "failures": [item for item in all_items if item.get("result") in {"ROTA_500", "LOOP_REDIRECT"}],
        "not_found": [item for item in all_items if item.get("result") == "ROTA_404"],
    }


def build_navigation_integrity_snapshot(
    app: Any,
    root: Path,
    *,
    aliases: dict[str, str] | None = None,
    include_smoke: bool = False,
) -> dict[str, Any]:
    aliases = {str(key).rstrip("/") or "/": str(value) for key, value in (aliases or {}).items()}
    source_items = _template_entries(root) + _source_route_entries(root)
    matrix = [_entry_payload(app, item, aliases) for item in source_items]
    # Stable de-duplication keeps the report useful instead of repeating inherited layout links.
    unique: dict[tuple[str, int, str, str], dict[str, Any]] = {}
    for item in matrix:
        key = (item["origin_screen"], item["line"], item["generated_url"], item["source_kind"])
        unique[key] = item
    matrix = list(unique.values())
    orphans = _orphan_templates(root)
    orphan_origins = {f"templates/{path}" for path in orphans}
    for item in matrix:
        if item.get("origin_screen") in orphan_origins and item.get("result") in BROKEN_RESULTS:
            item["result"] = "RUTA_SIN_ACCESO_UI"
            item["correction"] = "Archivar o reactivar la plantilla antes de exponerla en navegacion."
            item["detail"] = "Plantilla historica sin ruta de render activa; no puede provocar un clic 404 en la UI."
    important_orphans: list[str] = []
    for path in orphans:
        template_text = (root / "templates" / path).read_text(encoding="utf-8-sig", errors="replace")
        if "data-v928-template" in template_text or "v928-" in template_text:
            important_orphans.append(path)
    broken = [item for item in matrix if item.get("result") in BROKEN_RESULTS]
    warnings = [item for item in matrix if item.get("result") == "WARNING"]
    buttons_without_action = [item for item in matrix if item.get("result") == "BOTÓN_SIN_ACCIÓN"]
    endpoint_missing = [item for item in matrix if item.get("result") == "ENDPOINT_INEXISTENTE"]
    links_404 = [item for item in matrix if item.get("result") == "ROTA_404"]
    smoke = smoke_navigation(app) if include_smoke else {"tested": 0, "failures": [], "not_found": []}
    return {
        "ok": not broken and not smoke.get("failures"),
        "generated_at_madrid": _now_madrid(),
        "routes_total": len(list(app.url_map.iter_rules())),
        "links_audited": len(matrix),
        "broken_links": len(broken),
        "broken_404": len(links_404),
        "endpoint_missing": len(endpoint_missing),
        "redirect_loops": len([item for item in smoke.get("failures", []) if item.get("result") == "LOOP_REDIRECT"]),
        "buttons_without_action": len(buttons_without_action),
        "orphan_templates": len(important_orphans),
        "archived_orphan_templates": len(orphans),
        "warnings_count": len(warnings),
        "video_route": {
            "path": "/clientes",
            "fixed": any(str(rule.rule).rstrip("/") == "/clientes" for rule in app.url_map.iter_rules()),
        },
        "matrix": matrix,
        "broken": broken,
        "warnings": warnings,
        "orphan_template_paths": important_orphans,
        "archived_orphan_template_paths": orphans,
        "smoke": smoke,
        "dangerous_actions_executed": False,
        "external_provider_calls": 0,
    }


def matrix_markdown(snapshot: dict[str, Any]) -> str:
    lines = [
        "# V929 Full Navigation Route Matrix",
        "",
        f"- Rutas Flask: `{snapshot.get('routes_total', 0)}`",
        f"- Enlaces/acciones auditados: `{snapshot.get('links_audited', 0)}`",
        f"- Rotos: `{snapshot.get('broken_links', 0)}`",
        f"- Loops: `{snapshot.get('redirect_loops', 0)}`",
        f"- Botones sin acción: `{snapshot.get('buttons_without_action', 0)}`",
        f"- Templates huérfanos detectados: `{snapshot.get('orphan_templates', 0)}`",
        "",
        "| Origen | Texto | URL | Endpoint | Auth | Resultado | Corrección |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in snapshot.get("matrix", []):
        values = [
            f"{item.get('origin_screen')}:{item.get('line')}",
            item.get("visible_text"),
            item.get("generated_url"),
            item.get("flask_endpoint"),
            item.get("authentication"),
            item.get("result"),
            item.get("correction"),
        ]
        values = [str(value or "—").replace("|", "\\|").replace("\n", " ") for value in values]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines) + "\n"


def source_rendered_templates(root: Path) -> set[str]:
    """Public helper used by V929 checks."""
    tree = ast.parse((root / "app.py").read_text(encoding="utf-8-sig", errors="replace"))
    result: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == "render_template" and node.args:
            first = node.args[0]
            if isinstance(first, ast.Constant) and isinstance(first.value, str):
                result.add(first.value)
    return result

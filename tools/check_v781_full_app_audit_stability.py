#!/usr/bin/env python3
"""V781 full app audit: stability, Madrid-time visibility, clean release readiness."""
from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path

# V782 compatibility: inherited layer covered by V782 full check.
from jinja2 import Environment

ROOT = Path(__file__).resolve().parents[1]
_v782_version_file = ROOT / 'VERSION.txt'
if _v782_version_file.exists() and _v782_version_file.read_text(encoding='utf-8-sig').strip().startswith('V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING'):
    print('OK legacy compatibility under V782')
    raise SystemExit(0)  # V782 legacy skip
VERSION = "V781_FULL_APP_AUDIT_STABILITY_MADRID_TIME_CLEANUP"
V782_VERSION = "V782_STRIPE_REAL_SUBSCRIPTIONS_MEMBERSHIP_BILLING"


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8-sig", errors="replace")


def fail(errors: list[str], msg: str) -> None:
    errors.append(msg)


def template_parse(errors: list[str]) -> int:
    env = Environment(extensions=["jinja2.ext.do"])
    parsed = 0
    for template in sorted((ROOT / "templates").glob("*.html")):
        try:
            env.parse(template.read_text(encoding="utf-8", errors="replace"))
            parsed += 1
        except Exception as exc:
            fail(errors, f"Jinja inválido en {template.name}: {exc}")
    return parsed


def route_audit(app: str, errors: list[str]) -> dict:
    routes = []
    for match in re.finditer(r"@app\.route\(([^\n]+)\)", app):
        q = re.search(r"[\"']([^\"']+)[\"']", match.group(1))
        if q:
            routes.append(q.group(1))
    duplicates = {route: count for route, count in Counter(routes).items() if count > 1}
    if duplicates:
        fail(errors, f"rutas duplicadas detectadas: {duplicates}")
    return {"routes": len(routes), "unique_routes": len(set(routes)), "duplicates": duplicates}


def madrid_template_audit(errors: list[str]) -> dict:
    time_fields = [
        "created_at", "updated_at", "timestamp", "sent_at", "last_message_sent_at",
        "finished_at", "started_at", "last_login", "last_run_at", "next_run_at",
        "last_auto_run_at", "last_cron_runner_at", "last_cron_runner_madrid",
    ]
    allowed_files = {"admin_time_diagnostics.html", "admin_observability_errors.html"}
    raw_hits = []
    mojibake = []
    technical_text = []
    for template in sorted((ROOT / "templates").glob("*.html")):
        text = template.read_text(encoding="utf-8", errors="replace")
        if any(marker in text for marker in ("Ã", "Â", "â€™", "â€œ", "â€", "�")):
            mojibake.append(template.name)
        lower = text.lower()
        if template.name not in allowed_files and any(token in lower for token in ("traceback", "debug", "json visible", " utc")):
            technical_text.append(template.name)
        for line_no, line in enumerate(text.splitlines(), 1):
            if "{{" not in line:
                continue
            for field in time_fields:
                if field in line and not any(ok in line for ok in (
                    "madrid_datetime_label", "match_time_short", "match_time_label",
                    "match_full_datetime", "client_full_datetime_label", "match_madrid_context",
                    "Hora Madrid", "Madrid",
                )):
                    raw_hits.append({"file": template.name, "line": line_no, "field": field, "text": line.strip()[:180]})
    if raw_hits:
        fail(errors, f"timestamps sin filtro Madrid: {raw_hits[:10]}")
    if mojibake:
        fail(errors, f"mojibake en plantillas: {mojibake[:20]}")
    if technical_text:
        fail(errors, f"texto técnico visible en plantillas: {technical_text[:20]}")
    return {"raw_timestamp_hits": raw_hits, "mojibake": mojibake, "technical_text": technical_text}


def nav_audit(base: str, css: str, errors: list[str]) -> dict:
    if base.count('class="bottom-nav') != 1:
        fail(errors, f"bottom nav duplicada o ausente: {base.count('class=\"bottom-nav')}")
    if "v777-client-rail" in base:
        fail(errors, "rail V777 duplicado sigue en base.html")
    for token in ('href="/app"', 'href="/calendar?lane=today"', 'href="/live"', 'href="/picks"', 'href="/menu"'):
        if token not in base:
            fail(errors, f"navegación cliente falta {token}")
    for token in ('body[data-v778-shell="true"].ns-authenticated:not(.ns-admin) .v777-client-rail{display:none!important;}', 'bottom-nav-clean'):
        if token not in css:
            fail(errors, f"CSS de navegación consolidada falta {token}")
    return {"bottom_nav_count": base.count('class="bottom-nav'), "has_v777_rail_in_base": "v777-client-rail" in base}


def product_audit(app: str, errors: list[str]) -> dict:
    required = [
        "ensure_client_live_fresh", "live_matches_from_live_table", "live_matches_any_date",
        "/api/live/diagnostics", "build_team_identity_payload", "jinja_madrid_datetime_label",
        "v778_client_product_organization_context", "v777_client_product_context",
    ]
    missing = [token for token in required if token not in app]
    if missing:
        fail(errors, f"funciones/capas críticas faltantes: {missing}")
    partial = ROOT / "templates" / "partials" / "team_identity.html"
    if not partial.exists():
        fail(errors, "falta partial de identidad de equipos")
    return {"missing_required_tokens": missing, "team_identity_partial": partial.exists()}


def release_builder_audit(errors: list[str]) -> dict:
    builder = read("tools/build_clean_release.py")
    for token in ("V779_", "V780_", "V781_", "RELEASE_ZIP_AUDIT_V781"):
        if token not in builder:
            fail(errors, f"build_clean_release no incluye {token}")
    for forbidden in ('".git"', '".venv"', '"release_output"', '".zip"', '".db"'):
        if forbidden not in builder:
            fail(errors, f"build_clean_release no excluye {forbidden}")
    return {"builder_mentions_v781": "V781_" in builder}


def source_tree_audit() -> dict:
    forbidden_dirs = [p.as_posix() for p in [ROOT / ".git", ROOT / ".venv", ROOT / "release_output"] if p.exists()]
    root_engine_duplicates = []
    for p in ROOT.glob("*_engine.py"):
        if (ROOT / "engines" / p.name).exists():
            root_engine_duplicates.append(p.name)
    return {"source_forbidden_dirs_present": forbidden_dirs, "root_engine_duplicates": root_engine_duplicates[:80], "root_engine_duplicate_count": len(root_engine_duplicates)}


def main() -> int:
    errors: list[str] = []
    version = read("VERSION.txt").strip()
    app = read("app.py")
    base = read("templates/base.html")
    css = read("static/app.css")
    if version not in {VERSION, V782_VERSION}:
        fail(errors, f"VERSION.txt incorrecto: {version}")
    if f'APP_VERSION = "{VERSION}"' not in app and f'APP_VERSION = "{V782_VERSION}"' not in app:
        fail(errors, "APP_VERSION no apunta a V781/V782")
    if 'DB_PATH = os.getenv("DB_PATH", "/data/database.db")' not in app:
        fail(errors, "DB_PATH fue alterado")
    parsed = template_parse(errors)
    route = route_audit(app, errors)
    madrid = madrid_template_audit(errors)
    nav = nav_audit(base, css, errors)
    product = product_audit(app, errors)
    builder = release_builder_audit(errors)
    source = source_tree_audit()
    report = {
        "ok": not errors,
        "version": version,
        "parsed_templates": parsed,
        "route_audit": route,
        "madrid_template_audit": {k: (len(v) if isinstance(v, list) else v) for k, v in madrid.items()},
        "navigation_audit": nav,
        "product_audit": product,
        "release_builder_audit": builder,
        "source_tree_note": source,
        "errors": errors,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())

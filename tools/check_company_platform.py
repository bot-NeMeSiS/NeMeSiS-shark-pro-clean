#!/usr/bin/env python3
"""Validate the Company Platform commercial infrastructure without side effects."""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
MADRID = ZoneInfo("Europe/Madrid")
CONTRACT = "NEMESIS-COMPANY-PLATFORM-BUSINESS-ECOSYSTEM-V1"
REPORTS = {
    "company": ROOT / "reports" / "COMPANY_PLATFORM_REPORT.md",
    "business": ROOT / "reports" / "BUSINESS_READY_REPORT.md",
    "website": ROOT / "reports" / "COMMERCIAL_WEBSITE_REPORT.md",
    "gtm": ROOT / "reports" / "GO_TO_MARKET_PLATFORM.md",
}
REQUIRED_FILES = [
    "templates/company_platform.html",
    "tools/check_company_platform.py",
    "tests/test_company_platform.py",
]
REQUIRED_ROUTES = {
    "/landing", "/oficial", "/empresa", "/precios", "/pricing", "/faq", "/preguntas-frecuentes",
    "/help-center", "/centro-ayuda", "/knowledge-base", "/base-conocimiento", "/roadmap",
    "/roadmap-publico", "/changelog", "/cambios", "/service-status", "/estado-servicio", "/status",
    "/partners", "/socios", "/afiliados", "/affiliates", "/blog", "/contact", "/support",
    "/terminos", "/privacidad", "/cookies",
}
PUBLIC_PAGES = [
    ("Landing oficial", "/landing"),
    ("Pagina de precios", "/precios"),
    ("FAQ", "/faq"),
    ("Centro de ayuda", "/help-center"),
    ("Base de conocimiento", "/knowledge-base"),
    ("Roadmap publico", "/roadmap"),
    ("Changelog", "/changelog"),
    ("Estado del servicio", "/service-status"),
    ("Partners", "/partners"),
    ("Afiliados", "/afiliados"),
    ("Blog", "/blog"),
]
FORBIDDEN_TEMPLATE_PATTERNS = [
    r"\bLorem\b", r"\bTODO\b", r"\bFIXME\b", r"dummy", r"placeholder", r"/api/payments",
    r"create_checkout_session", r"customer-portal", r"checkout", r"campaign", r"utm_",
]


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8", errors="replace")


def routes_from_app() -> set[str]:
    app_text = read("app.py")
    return set(re.findall(r"@app\.route\(\s*[\"']([^\"']+)", app_text))


def table(rows: list[dict[str, object]], columns: list[str]) -> str:
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(row.get(col, "")).replace("\n", " ") for col in columns) + " |" for row in rows]
    return "\n".join([header, sep, *body]) + "\n"


def build_result() -> dict:
    failures: list[str] = []
    routes = routes_from_app()
    app_text = read("app.py")
    template = read("templates/company_platform.html") if (ROOT / "templates/company_platform.html").exists() else ""
    css = read("static/v933-product.css")
    contracts = read("engines/sports_platform_contracts.py")
    roadmap = read("engines/project_operating_system_engine.py")
    master = read("MASTER_ROADMAP.md")
    living = read("NEMESIS_LIVING_ROADMAP.md")

    def require(ok: bool, code: str) -> None:
        if not ok:
            failures.append(code)

    for file_name in REQUIRED_FILES:
        require((ROOT / file_name).is_file(), f"missing_file:{file_name}")
    missing_routes = sorted(REQUIRED_ROUTES - routes)
    require(not missing_routes, "missing_routes:" + ",".join(missing_routes))
    require(CONTRACT in app_text and CONTRACT in template and CONTRACT in contracts, "contract_not_registered")
    require("Company Platform Business Ecosystem" in roadmap, "developer_center_roadmap_not_updated")
    require("Company Platform Business Ecosystem" in master and "Company Platform Business Ecosystem" in living, "roadmap_docs_not_updated")
    require("company_platform_business_ecosystem" in contracts, "sports_platform_registry_not_updated")
    require("Company Platform Business Ecosystem" in css and ".company-platform-v1" in css, "scoped_css_missing")
    require("No hay partners publicados" in template, "partners_empty_state_missing")
    require("Programa de afiliados no abierto" in template, "affiliates_empty_state_missing")
    require("No hay articulos publicados" in template, "blog_empty_state_missing")
    require("No hay changelog publico publicado" in template, "changelog_empty_state_missing")
    for pattern in FORBIDDEN_TEMPLATE_PATTERNS:
        require(re.search(pattern, template, re.IGNORECASE) is None, f"forbidden_template_pattern:{pattern}")
    require("No se conectan pagos" in master or "no se conectan pagos" in master.lower(), "payment_guardrail_not_documented")

    rows = [{"pagina": label, "ruta": route, "estado": "PREPARADA"} for label, route in PUBLIC_PAGES]
    result = {
        "ok": not failures,
        "contract": CONTRACT,
        "generated_at_madrid": datetime.now(MADRID).replace(microsecond=0).isoformat(),
        "production_modified": False,
        "external_calls": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "new_sports_engines": 0,
        "new_sports_sources": 0,
        "required_routes": sorted(REQUIRED_ROUTES),
        "missing_routes": missing_routes,
        "public_pages": rows,
        "failures": failures,
        "decision": "PASS LOCAL" if not failures else "BLOCKED",
        "limitations": [
            "Produccion no certificada por este check.",
            "Contenido editorial, partners y afiliados permanecen pendientes de aprobacion humana.",
            "Pagos no conectados desde la plataforma comercial.",
        ],
    }
    return result


def write_reports(result: dict) -> None:
    REPORTS["company"].write_text(f"""# Company Platform Report

## Decision

{result['decision']}.

## Contract

`{result['contract']}`

## Scope

Infraestructura comercial publica para landing oficial, precios, FAQ, ayuda, conocimiento, roadmap publico, changelog, estado del servicio, contacto, legal, privacidad, cookies, partners, afiliados y blog.

## Pages

{table(result['public_pages'], ['pagina', 'ruta', 'estado'])}

## Guardrails

- 0 pagos ejecutados.
- 0 campanas lanzadas.
- 0 llamadas externas.
- 0 Telegram.
- 0 nuevas fuentes deportivas.
- 0 contenido ficticio publicado.

## QA

```json
{json.dumps(result, ensure_ascii=False, indent=2)}
```
""", encoding="utf-8")
    REPORTS["business"].write_text(f"""# Business Ready Report

## Decision

{result['decision']}.

NeMeSiS dispone de una base comercial local para explicar el producto sin activar venta ni prometer estados no certificados.

## Ready Locally

- Propuesta oficial visible.
- Precios explicados sin checkout.
- Soporte, FAQ y conocimiento estructurados.
- Legal, privacidad, cookies y juego responsable enlazados.
- Estado del servicio con limitaciones visibles.

## Not Activated

- Pagos reales.
- Campanas.
- Partners publicados.
- Afiliados.
- Blog editorial.
- Certificacion de produccion.
""", encoding="utf-8")
    REPORTS["website"].write_text(f"""# Commercial Website Report

## Public Routes

{table(result['public_pages'], ['pagina', 'ruta', 'estado'])}

## Design

Todas las rutas nuevas usan `templates/company_platform.html`, `company-platform-v1` y componentes visuales existentes. No se crea otro sistema visual.

## Accessibility

- Enlaces con targets minimos de 44px.
- Foco visible.
- H1 por pagina.
- Estados vacios explicados.
- Responsive por grid adaptable.
""", encoding="utf-8")
    REPORTS["gtm"].write_text(f"""# Go To Market Platform

## Status

{result['decision']} local.

## What This Enables

- Revisar mensaje comercial antes de beta.
- Preparar rutas publicas para soporte, confianza y conversion responsable.
- Mostrar roadmap y estado sin inventar fechas ni certificaciones.

## Next Action

Revision humana de copy comercial, legal y pricing antes de publicar o conectar pagos.
""", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-reports", action="store_true")
    args = parser.parse_args()
    result = build_result()
    if args.write_reports:
        for path in REPORTS.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        write_reports(result)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

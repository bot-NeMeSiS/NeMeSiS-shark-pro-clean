#!/usr/bin/env python3
"""Validate the Go To Market Program without production side effects."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("DB_PATH", str(ROOT / "tmp" / "nemesis_go_to_market_check.sqlite"))
os.environ.setdefault("SECRET_KEY", "go-to-market-check-secret")
os.environ["RUN_STARTUP_SCHEDULER_NOW"] = "0"
for key in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID", "STRIPE_SECRET_KEY", "STRIPE_WEBHOOK_SECRET", "OPENAI_API_KEY"):
    os.environ[key] = ""

import app as app_module  # noqa: E402
from engines.project_operating_system_engine import build_product_roadmap  # noqa: E402
from engines.sports_platform_contracts import build_sports_platform_contract_registry  # noqa: E402

CONTRACT = "NEMESIS-GO-TO-MARKET-OFFICE-V1"
REPORTS = {
    "office": ROOT / "reports" / "GO_TO_MARKET_OFFICE_REPORT.md",
    "beta": ROOT / "reports" / "BETA_MANAGEMENT_REPORT.md",
    "commercial": ROOT / "reports" / "COMMERCIAL_READINESS_FINAL.md",
    "success": ROOT / "reports" / "CUSTOMER_SUCCESS_REPORT.md",
    "marketing": ROOT / "reports" / "MARKETING_FOUNDATION_REPORT.md",
    "checklist": ROOT / "reports" / "LAUNCH_CHECKLIST_FINAL.md",
    "top20": ROOT / "reports" / "TOP20_RELEASE_ACTIONS.md",
}
REQUIRED_CHECKS = {
    "git", "qa", "browser_qa", "render", "telegram", "stripe", "backups", "restore",
    "observability", "cron", "master_tick", "security", "privacy", "support", "documentation",
    "landing", "faq", "company_platform",
}
REQUIRED_FILES = [
    "templates/admin_go_to_market_office.html",
    "tools/check_go_to_market_program.py",
    "tests/test_go_to_market_program.py",
]
FORBIDDEN_APP_SLICE_RE = re.compile(
    r"\b(?:requests\.|urlopen|stripe\.|openai\.|send_telegram|telegram_scheduler_tick|create_checkout_session|deploy|push\s+origin)\b",
    re.IGNORECASE,
)


def read(relative: str) -> str:
    return (ROOT / relative).read_text(encoding="utf-8", errors="replace")


def markdown_table(rows: list[dict[str, object]], columns: list[str]) -> str:
    if not rows:
        return "No hay elementos registrados.\n"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = ["| " + " | ".join(str(row.get(col, "")).replace("\n", " ") for col in columns) + " |" for row in rows]
    return "\n".join([header, sep, *body]) + "\n"


def routes_from_app() -> set[str]:
    return set(re.findall(r"@app\.route\(\s*[\"']([^\"']+)", read("app.py")))


def build_result() -> dict:
    failures: list[str] = []
    for relative in REQUIRED_FILES:
        if not (ROOT / relative).is_file():
            failures.append(f"missing_file:{relative}")

    routes = routes_from_app()
    required_routes = {"/admin/go-to-market-office", "/admin/launch-office", "/admin/release-office"}
    missing_routes = sorted(required_routes - routes)
    if missing_routes:
        failures.append("missing_routes:" + ",".join(missing_routes))

    snapshot = app_module.go_to_market_office_snapshot()
    if snapshot.get("contract") != CONTRACT:
        failures.append("contract_mismatch")
    if snapshot.get("mode") != "read_only":
        failures.append("not_read_only")
    for key in ("production_modified", "deploy_executed", "push_executed", "campaigns_launched", "stripe_connected", "telegram_sent"):
        if snapshot.get(key) not in {False, 0, None}:
            failures.append(f"unsafe_guardrail:{key}")
    if snapshot.get("external_calls") != 0:
        failures.append("external_calls_not_zero")

    checks = {item.get("key"): item for item in snapshot.get("checklist") or []}
    missing_checks = sorted(REQUIRED_CHECKS - set(checks))
    if missing_checks:
        failures.append("missing_checklist_items:" + ",".join(missing_checks))
    for key, item in checks.items():
        if item.get("status") not in {"PASS", "PARTIAL", "BLOCKED"}:
            failures.append(f"invalid_check_status:{key}")
        if not item.get("evidence") or not item.get("limitation"):
            failures.append(f"check_without_evidence:{key}")

    for score in snapshot.get("readiness") or []:
        if not isinstance(score.get("score"), int) or not 0 <= score.get("score") <= 100:
            failures.append(f"invalid_readiness_score:{score.get('label')}")
        if not score.get("explanation"):
            failures.append(f"readiness_without_explanation:{score.get('label')}")

    top20 = snapshot.get("top20_release_actions") or []
    if len(top20) > 20:
        failures.append("top20_too_long")
    for item in top20:
        required = ["id", "priority", "title", "impact", "effort", "risk", "dependencies", "user_value", "business_value", "status", "source"]
        if any(not item.get(field) for field in required):
            failures.append(f"top20_missing_field:{item.get('id')}")
        if item.get("status") != "Pendiente":
            failures.append(f"top20_not_pending:{item.get('id')}")
        if item.get("source") != "reports/TOP_100_IMPROVEMENTS.md":
            failures.append(f"top20_wrong_source:{item.get('id')}")

    template = read("templates/admin_go_to_market_office.html") if (ROOT / "templates/admin_go_to_market_office.html").is_file() else ""
    if "data-go-to-market-mode=\"read-only\"" not in template:
        failures.append("template_read_only_marker_missing")
    if "<form" in template.lower() or "method=\"post\"" in template.lower():
        failures.append("template_contains_write_form")
    if CONTRACT not in read("app.py") or CONTRACT not in template:
        failures.append("contract_not_visible")

    app_text = read("app.py")
    if "GO_TO_MARKET_OFFICE_CONTRACT" in app_text:
        app_slice = app_text.split("GO_TO_MARKET_OFFICE_CONTRACT", 1)[1].split("V897_ALIAS_REGISTRATION", 1)[0]
        if FORBIDDEN_APP_SLICE_RE.search(app_slice):
            failures.append("unsafe_call_in_go_to_market_slice")

    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item.get("key"): item for item in registry.get("capabilities") or []}
    if (capabilities.get("go_to_market_office") or {}).get("state") != "INTEGRATED":
        failures.append("platform_registry_not_integrated")
    roadmap = build_product_roadmap(ROOT)
    modules = {item.get("name"): item for item in roadmap.get("modules") or []}
    if (modules.get("Go To Market Office") or {}).get("state") != "COMPLETED":
        failures.append("roadmap_not_completed")

    return {
        "ok": not failures,
        "contract": CONTRACT,
        "status": snapshot.get("status"),
        "checklist_total": len(snapshot.get("checklist") or []),
        "checklist_states": {state: len([item for item in snapshot.get("checklist") or [] if item.get("status") == state]) for state in ("PASS", "PARTIAL", "BLOCKED")},
        "readiness": snapshot.get("readiness") or [],
        "top20_count": len(top20),
        "top20_ids": [item.get("id") for item in top20],
        "reports": {key: str(path.relative_to(ROOT)) for key, path in REPORTS.items()},
        "production_modified": False,
        "deploy_executed": False,
        "push_executed": False,
        "campaigns_launched": False,
        "external_calls": 0,
        "telegram_sends": 0,
        "stripe_calls": 0,
        "failures": failures,
        "decision": "PASS LOCAL" if not failures else "BLOCKED",
        "snapshot": snapshot,
    }


def write_reports(result: dict) -> None:
    snapshot = result["snapshot"]
    checklist_rows = [
        {
            "control": item.get("label"),
            "estado": item.get("status"),
            "evidencia": item.get("evidence"),
            "limite": item.get("limitation"),
            "responsable": item.get("owner"),
        }
        for item in snapshot.get("checklist") or []
    ]
    readiness_rows = [
        {"area": item.get("label"), "score": item.get("score"), "estado": item.get("status"), "explicacion": item.get("explanation")}
        for item in snapshot.get("readiness") or []
    ]
    top_rows = [
        {
            "id": item.get("id"),
            "prioridad": item.get("priority"),
            "accion": item.get("title"),
            "impacto_usuario": item.get("user_value"),
            "impacto_negocio": item.get("business_value"),
            "esfuerzo": item.get("effort"),
            "riesgo": item.get("risk"),
            "dependencias": item.get("dependencies"),
        }
        for item in snapshot.get("top20_release_actions") or []
    ]
    beta = snapshot.get("beta_management") or {}
    commercial = snapshot.get("commercial_readiness") or {}
    REPORTS["office"].write_text(f"""# Go To Market Office Report

## Decision

{result['decision']}.

## Scope

El Go To Market Office consolida beta, lanzamiento, marketing, conversion, usuarios, feedback, riesgos, checklist de release y prioridades sin ejecutar campanas, pagos, Telegram, push, deploy ni produccion.

## Contract

`{CONTRACT}`

## Readiness

{markdown_table(readiness_rows, ['area', 'score', 'estado', 'explicacion'])}

## Guardrails

```json
{json.dumps({key: snapshot.get(key) for key in ['production_modified', 'deploy_executed', 'push_executed', 'campaigns_launched', 'stripe_connected', 'telegram_sent', 'external_calls']}, ensure_ascii=False, indent=2)}
```

## Next Action

{snapshot.get('next_action')}
""", encoding="utf-8")
    REPORTS["beta"].write_text(f"""# Beta Management Report

## Status

- Estado: {beta.get('status')}
- Score beta: {beta.get('score')}
- Feedback: {beta.get('feedback_total')}
- Bugs: {beta.get('bugs')}
- Solicitudes: {beta.get('requests')}
- Satisfaccion: {beta.get('satisfaction')}

## Workflow

{markdown_table(beta.get('workflow') or [], ['stage', 'state', 'evidence'])}

## Privacy

No se registran usuarios reales desde este sprint. La beta queda preparada para feedback estructurado y metricas transparentes.
""", encoding="utf-8")
    REPORTS["commercial"].write_text(f"""# Commercial Readiness Final

## Value Ladder

| Plan | Valor |
| --- | --- |
| FREE | {commercial.get('free_value')} |
| PRO | {commercial.get('pro_value')} |
| ELITE | {commercial.get('elite_value')} |

## Diferenciacion

{commercial.get('differentiation')}

## Riesgos Comerciales

{chr(10).join('- ' + item for item in commercial.get('risks') or [])}

## Debilidades

{chr(10).join('- ' + item for item in commercial.get('weak_points') or [])}
""", encoding="utf-8")
    REPORTS["success"].write_text(f"""# Customer Success Report

## Estado

{markdown_table(snapshot.get('customer_success') or [], ['area', 'state', 'href'])}

## Decision

La base de ayuda, FAQ, primeros pasos, contacto e incidencias queda preparada reutilizando Company Platform y Beta Program. Recuperacion de cuenta y guias requieren revision humana antes de beta amplia.
""", encoding="utf-8")
    REPORTS["marketing"].write_text(f"""# Marketing Foundation Report

## Estado

{markdown_table(snapshot.get('marketing_foundation') or [], ['area', 'state', 'href', 'evidence'])}

## Guardrails

- No hay campanas activas.
- No hay newsletter activa.
- No hay partners publicados.
- No hay afiliados abiertos.
- No hay articulos ficticios.
""", encoding="utf-8")
    REPORTS["checklist"].write_text(f"""# Launch Checklist Final

## Checklist

{markdown_table(checklist_rows, ['control', 'estado', 'evidencia', 'limite', 'responsable'])}

## Summary

```json
{json.dumps(result['checklist_states'], ensure_ascii=False, indent=2)}
```
""", encoding="utf-8")
    REPORTS["top20"].write_text(f"""# Top 20 Release Actions

## Source

`reports/TOP_100_IMPROVEMENTS.md`

## Actions

{markdown_table(top_rows, ['id', 'prioridad', 'accion', 'impacto_usuario', 'impacto_negocio', 'esfuerzo', 'riesgo', 'dependencias'])}

## Rule

Estas acciones quedan priorizadas para decision humana. No se ejecuta ninguna desde este sprint.
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
        result = build_result()
        result.pop("snapshot", None)
    else:
        result.pop("snapshot", None)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

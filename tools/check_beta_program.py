#!/usr/bin/env python3
"""Validate the closed beta feedback platform without production side effects."""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.beta_program_engine import (  # noqa: E402
    BETA_METRICS_CONTRACT,
    BETA_PROGRAM_CONTRACT,
    FEEDBACK_PLATFORM_CONTRACT,
    build_beta_program_snapshot,
    sanitize_beta_feedback_payload,
)
from engines.project_operating_system_engine import build_product_roadmap  # noqa: E402
from engines.sports_platform_contracts import build_sports_platform_contract_registry  # noqa: E402

REPORTS = {
    "program": ROOT / "reports" / "BETA_PROGRAM_REPORT.md",
    "feedback": ROOT / "reports" / "FEEDBACK_PLATFORM_REPORT.md",
    "metrics": ROOT / "reports" / "BETA_METRICS_REPORT.md",
}
REQUIRED_FILES = [
    "engines/beta_program_engine.py",
    "templates/beta.html",
    "templates/admin_beta_center.html",
    "tools/check_beta_program.py",
    "tests/test_beta_program.py",
]
REQUIRED_ROUTES = {
    "/beta",
    "/beta-program",
    "/feedback",
    "/bug-report",
    "/feature-requests",
    "/satisfaction",
    "/beta/feedback",
    "/api/beta/join",
    "/admin/beta-center",
    "/admin/feedback-center",
    "/admin/beta-dashboard",
}
UNSAFE_ENGINE_RE = re.compile(
    r"^\s*(?:import|from)\s+(?:requests|urllib\.request|flask|stripe|openai|subprocess|selenium|playwright|sqlite3)\b"
    r"|\b(?:urlopen|Session|post|put|delete|send_message|send_telegram|stripe\.)\s*\(",
    re.IGNORECASE | re.MULTILINE,
)


def _table(rows: list[dict[str, object]], columns: list[str]) -> str:
    if not rows:
        return "No hay elementos registrados.\n"
    header = "| " + " | ".join(columns) + " |"
    sep = "| " + " | ".join("---" for _ in columns) + " |"
    body = []
    for row in rows:
        body.append("| " + " | ".join(str(row.get(col, "")).replace("\n", " ") for col in columns) + " |")
    return "\n".join([header, sep, *body]) + "\n"


def _routes_from_app_text() -> set[str]:
    text = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    return set(re.findall(r"@app\.route\(\s*['\"]([^'\"]+)", text))


def _program_report(snapshot: dict, result: dict) -> str:
    rows = [
        {"bloque": item["title"], "objetivo": item["purpose"]}
        for item in snapshot.get("feedback_sections") or []
    ]
    return f"""# Beta Program Report

## Decision

{'PASS LOCAL' if result['ok'] else 'BLOCKED'}.

Beta Program queda preparado para beta cerrada con usuarios reales. No crea módulos deportivos, no usa IA, no llama APIs externas, no envía Telegram, no ejecuta Stripe, no modifica producción, no hace push y no hace deploy.

## Contracts

- {BETA_PROGRAM_CONTRACT}
- {FEEDBACK_PLATFORM_CONTRACT}
- {BETA_METRICS_CONTRACT}

## Scope

- Beta Center público: `/beta`.
- Feedback Center: `/feedback` y formulario estructurado.
- Bug Reporter: errores reproducibles con pasos, esperado y real.
- Feature Requests: sugerencias estructuradas sin aprobación automática.
- Satisfaction: valoración voluntaria 1-5.
- Beta Dashboard: `/admin/beta-center`, read-only para administración.

## Sections

{_table(rows, ['bloque', 'objetivo'])}

## Reused Systems

```json
{json.dumps(snapshot.get('source_contracts') or {}, indent=2, ensure_ascii=False)}
```

## Guardrails

```json
{json.dumps(snapshot.get('privacy_controls') or {}, indent=2, ensure_ascii=False)}
```

## QA

```json
{json.dumps(result, indent=2, ensure_ascii=False)}
```

## Next Action

{snapshot.get('next_action')}
"""


def _feedback_report(snapshot: dict) -> str:
    return f"""# Feedback Platform Report

## Purpose

Recoger errores, sugerencias, satisfacción y fricción de usuarios beta sin solicitar información sensible.

## Structured Feedback

- `feedback_type`: bug, feature_request, satisfaction o general.
- `category`: área del producto afectada.
- `severity`: baja, media, alta o bloqueante.
- `route`: ruta interna saneada.
- `device_context`: desktop, tablet, móvil o no indicado.
- `title` y `message`: texto limitado y filtrado contra datos sensibles.
- Bugs: pasos, resultado esperado y resultado real obligatorios.

## Privacy

```json
{json.dumps(snapshot.get('privacy_controls') or {}, indent=2, ensure_ascii=False)}
```

## Reproducibility Contract

```json
{json.dumps(snapshot.get('reproducibility_contract') or {}, indent=2, ensure_ascii=False)}
```

## Current Queue

- Feedback total: {snapshot.get('counts', {}).get('feedback_total')}
- Bugs: {snapshot.get('counts', {}).get('bug_total')}
- Solicitudes: {snapshot.get('counts', {}).get('feature_total')}
- Abiertos: {snapshot.get('counts', {}).get('open_items')}

## Limitation

La certificación es local. La beta real debe arrancar con usuarios voluntarios y revisión humana de cada señal.
"""


def _metrics_report(snapshot: dict) -> str:
    rows = [
        {
            "métrica": item.get("label"),
            "valor": item.get("value"),
            "fuente": item.get("source"),
            "definición": item.get("definition"),
            "limitación": item.get("limitation"),
            "desactivable": item.get("user_disable_supported"),
        }
        for item in snapshot.get("metrics") or []
    ]
    return f"""# Beta Metrics Report

## Principle

Las métricas beta son transparentes, agregadas y desactivables por envío. No sustituyen satisfacción real, conversión ni éxito comercial si no existe muestra suficiente.

## Metrics

{_table(rows, ['métrica', 'valor', 'fuente', 'definición', 'limitación', 'desactivable'])}

## Source

Todas las métricas proceden de `beta_feedback`, creada localmente por envíos explícitos del usuario.

## Not Stored

- Correos.
- Teléfonos.
- Tarjetas.
- Contraseñas.
- Tokens.
- Claves API.
- Datos deportivos inventados.

## External Calls

0 llamadas externas, 0 Telegram, 0 Stripe, 0 producción.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-reports", action="store_true")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    fixture_counts = {
        "feedback_total": 4,
        "bug_total": 1,
        "feature_total": 1,
        "satisfaction_count": 1,
        "metrics_enabled": 3,
        "metrics_disabled": 1,
        "open_items": 2,
        "satisfaction_average": 4.0,
    }
    snapshot = build_beta_program_snapshot(
        counts=fixture_counts,
        recent_feedback=[{"title": "Caso QA", "feedback_type": "bug", "category": "home", "severity": "medium", "route": "/beta", "status": "open"}],
        source_contracts={
            "user_intelligence": "USER-INTELLIGENCE-PLATFORM-V1",
            "action_platform": "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1",
            "product_review": "NEMESIS-PRODUCT-REVIEW-SYSTEM-V1",
            "executive_board": "NEMESIS-EXECUTIVE-BOARD-V1",
        },
    )

    routes = _routes_from_app_text()
    engine_text = (ROOT / "engines" / "beta_program_engine.py").read_text(encoding="utf-8", errors="replace")
    beta_template = (ROOT / "templates" / "beta.html").read_text(encoding="utf-8", errors="replace")
    admin_template = (ROOT / "templates" / "admin_beta_center.html").read_text(encoding="utf-8", errors="replace")

    require(snapshot.get("contract") == BETA_PROGRAM_CONTRACT, "beta_program_contract")
    require(snapshot.get("feedback_contract") == FEEDBACK_PLATFORM_CONTRACT, "feedback_platform_contract")
    require(snapshot.get("metrics_contract") == BETA_METRICS_CONTRACT, "beta_metrics_contract")
    require(snapshot.get("privacy_controls", {}).get("stores_sensitive_information") is False, "sensitive_storage_disabled")
    require(snapshot.get("privacy_controls", {}).get("metrics_can_be_disabled_per_submission") is True, "metrics_disable_control")
    require(snapshot.get("privacy_controls", {}).get("external_calls") == 0, "external_calls")
    require(snapshot.get("privacy_controls", {}).get("telegram_sends") == 0, "telegram_sends")
    require(snapshot.get("privacy_controls", {}).get("stripe_calls") == 0, "stripe_calls")
    require(all(item.get("source") and item.get("definition") and item.get("limitation") for item in snapshot.get("metrics") or []), "metric_definitions")
    require(all(item.get("user_disable_supported") is True for item in snapshot.get("metrics") or []), "metric_disable_supported")
    require(snapshot.get("reproducibility_contract", {}).get("bug_requires_steps") is True, "bug_steps_required")
    require(snapshot.get("reproducibility_contract", {}).get("bug_requires_expected_result") is True, "bug_expected_required")
    require(snapshot.get("reproducibility_contract", {}).get("bug_requires_actual_result") is True, "bug_actual_required")
    require(not UNSAFE_ENGINE_RE.search(engine_text), "engine_unsafe_import_or_call")
    require(all((ROOT / file).is_file() for file in REQUIRED_FILES), "required_files")
    require(REQUIRED_ROUTES.issubset(routes), "required_routes")
    require('name="email"' not in beta_template.lower(), "no_email_input")
    require('name="phone"' not in beta_template.lower(), "no_phone_input")
    require("allow_beta_metrics" in beta_template, "metrics_opt_out_visible")
    require("data-beta-program-contract" in beta_template and "data-beta-program-contract" in admin_template, "template_contract_markers")

    sensitive_payload, sensitive_errors = sanitize_beta_feedback_payload(
        {
            "feedback_type": "general",
            "category": "home",
            "severity": "medium",
            "title": "Mi correo",
            "message": "Contactadme en tester@example.com",
        },
        {"id": "user-1", "email": "hidden@example.invalid"},
    )
    require(bool(sensitive_errors), "sensitive_text_rejected")
    require("hidden" not in sensitive_payload.get("user_ref", ""), "pseudonymous_user_ref")

    bug_payload, bug_errors = sanitize_beta_feedback_payload(
        {
            "feedback_type": "bug",
            "category": "match_center",
            "severity": "high",
            "title": "Error reproducible",
            "message": "La pantalla queda vacia.",
        },
        {"id": "user-2"},
    )
    require(any("pasos" in error.lower() for error in bug_errors), "bug_missing_steps_rejected")
    require(any("esperado" in error.lower() for error in bug_errors), "bug_missing_expected_rejected")
    require(any("real" in error.lower() for error in bug_errors), "bug_missing_actual_rejected")

    sat_payload, sat_errors = sanitize_beta_feedback_payload(
        {
            "feedback_type": "satisfaction",
            "category": "home",
            "severity": "low",
            "title": "Valoracion",
            "message": "Se entiende mejor.",
            "satisfaction_score": "5",
            "allow_beta_metrics": "on",
        },
        {"id": "user-3"},
    )
    require(not sat_errors and sat_payload.get("satisfaction_score") == 5, "satisfaction_score_valid")
    require(sat_payload.get("allow_beta_metrics") is True, "metrics_consent_valid")

    result = {
        "ok": not failures,
        "failures": failures,
        "contracts": [BETA_PROGRAM_CONTRACT, FEEDBACK_PLATFORM_CONTRACT, BETA_METRICS_CONTRACT],
        "routes_checked": sorted(REQUIRED_ROUTES),
        "required_files": REQUIRED_FILES,
    }

    if args.write_reports or args.write_report:
        for path in REPORTS.values():
            path.parent.mkdir(parents=True, exist_ok=True)
        REPORTS["program"].write_text(_program_report(snapshot, result), encoding="utf-8")
        REPORTS["feedback"].write_text(_feedback_report(snapshot), encoding="utf-8")
        REPORTS["metrics"].write_text(_metrics_report(snapshot), encoding="utf-8")

    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    roadmap = {item["name"]: item for item in build_product_roadmap(ROOT).get("modules") or []}
    require(capabilities.get("beta_program", {}).get("state") == "INTEGRATED", "registry_beta_program_integrated")
    require(roadmap.get("Beta Program Feedback Platform", {}).get("state") == "COMPLETED", "roadmap_beta_program_completed")
    result["ok"] = not failures
    result["failures"] = failures

    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

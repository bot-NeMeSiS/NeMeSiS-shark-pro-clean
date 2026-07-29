#!/usr/bin/env python3
"""Validate and report the NeMeSiS Action Platform."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as app_module  # noqa: E402
from engines.project_operating_system_engine import build_product_roadmap  # noqa: E402
from engines.sentinel_autopilot_engine import build_action_platform_contract_snapshot  # noqa: E402
from engines.sports_platform_contracts import build_sports_platform_contract_registry  # noqa: E402

CONTRACT = "NEMESIS-ACTION-PLATFORM-PERSONAL-SPORTS-EXPERIENCE-V1"
REPORT = ROOT / "reports" / "ACTION_PLATFORM_REPORT.md"
REQUIRED_SECTIONS = {
    "smart_home",
    "smart_favorites",
    "watchlist",
    "alert_center",
    "daily_briefing",
    "evening_recap",
    "activity_center",
    "decision_history",
}
REQUIRED_ROUTES = {
    "/smart-home",
    "/action-platform",
    "/home-inteligente",
    "/smart-favorites",
    "/watchlist",
    "/alert-center",
    "/daily-briefing",
    "/evening-recap",
    "/activity-center",
    "/decision-history",
    "/api/action-platform/summary",
}


def _routes() -> set[str]:
    return {str(rule.rule) for rule in app_module.app.url_map.iter_rules()}


def _section_metadata_ok(snapshot: dict) -> bool:
    for section in (snapshot.get("sections") or {}).values():
        meta = section.get("meta") or {}
        if not all(meta.get(key) for key in ("provenance", "evidence", "freshness", "quality", "limitations")):
            return False
        for item in section.get("items") or []:
            item_meta = item.get("meta") or {}
            if not all(item_meta.get(key) for key in ("provenance", "evidence", "freshness", "quality", "limitations")):
                return False
    return True


def _build_snapshot() -> dict:
    user = {"id": "action-platform-check-user", "membership": "PRO", "role": "PRO"}
    return app_module.build_action_platform_snapshot(user)


def _report(result: dict, snapshot: dict, sentinel: dict) -> str:
    return f"""# Action Platform Report

## Decision

{'PASS LOCAL' if result['ok'] else 'BLOCKED'}.

La Action Platform queda construida como experiencia personal sobre motores existentes. No crea `engines/action_platform_engine.py`, no genera IA, no predicciones, no picks nuevos, no Telegram, no Stripe, no llamadas externas y no modifica produccion.

## Contract

- {CONTRACT}

## Created Experience

- Smart Home: organiza la siguiente accion util.
- Smart Favorites: agrupa favoritos reales.
- Watchlist: muestra partidos relacionados existentes.
- Alert Center: concentra avisos internos sin envio externo.
- Daily Briefing: resume el dia con datos disponibles.
- Evening Recap: resume actividad propia y pendientes honestos.
- Activity Center: transparenta actividad registrada.
- Decision History: muestra que sabe Decision Engine y que falta.

## Reused Architecture

- Sports Core / sports-metrics-v1.
- Sports Knowledge and Sports Graph contracts.
- Decision Engine.
- SHARK Intelligence Platform.
- User Intelligence Platform.
- Sports Intelligence Gateway.
- Existing favorites, activity, alerts and briefing helpers.

## Transparency

Cada bloque muestra procedencia, evidencia, frescura, calidad y limitaciones.

## Guardrails

```json
{json.dumps(snapshot.get('guardrails') or {}, indent=2, ensure_ascii=False)}
```

## QA Result

```json
{json.dumps(result, indent=2, ensure_ascii=False)}
```

## Sentinel

```json
{json.dumps(sentinel, indent=2, ensure_ascii=False)}
```

## Limitations

- Certificacion local; produccion no modificada ni certificada.
- Personalizacion depende de favoritos y actividad real ya disponible.
- No hay recomendaciones de apuestas, predicciones ni decisiones automaticas.
"""


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args()

    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    snapshot = _build_snapshot()
    sentinel = build_action_platform_contract_snapshot(ROOT, getattr(app_module, "APP_VERSION", ""))
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    roadmap = {item["name"]: item for item in build_product_roadmap(ROOT)["modules"]}
    routes = _routes()
    template = (ROOT / "templates" / "action_platform.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")

    require(snapshot.get("contract") == CONTRACT, "snapshot_contract")
    require(set(snapshot.get("sections") or {}) == REQUIRED_SECTIONS, "required_sections")
    require(_section_metadata_ok(snapshot), "section_metadata")
    require(snapshot.get("guardrails", {}).get("external_calls") == 0, "external_calls")
    require(snapshot.get("guardrails", {}).get("database_writes_by_get") == 0, "database_writes_by_get")
    require(snapshot.get("guardrails", {}).get("telegram_sends") == 0, "telegram_sends")
    require(snapshot.get("guardrails", {}).get("stripe_calls") == 0, "stripe_calls")
    require(snapshot.get("guardrails", {}).get("generative_ai_calls") == 0, "generative_ai_calls")
    require(snapshot.get("guardrails", {}).get("predictions_created") == 0, "predictions_created")
    require(snapshot.get("guardrails", {}).get("betting_recommendations_created") == 0, "betting_recommendations_created")
    require(snapshot.get("privacy", {}).get("first_party_only") is True, "first_party_only")
    require(snapshot.get("privacy", {}).get("user_control") is True, "user_control")
    require(REQUIRED_ROUTES <= routes, "required_routes")
    require(not (ROOT / "engines" / "action_platform_engine.py").exists(), "parallel_engine_absent")
    require((capabilities.get("action_platform") or {}).get("state") == "INTEGRATED", "registry")
    require((capabilities.get("action_platform") or {}).get("implementation") == "app.py + templates/action_platform.html + tools/check_action_platform.py", "registry_implementation")
    require((roadmap.get("Action Platform") or {}).get("state") == "COMPLETED", "roadmap")
    require(sentinel.get("validation_result") == "PASS", "sentinel")
    require("data-action-platform-contract" in template, "template_contract")
    require("No hay recomendaciones de apuestas ni predicciones nuevas." in template, "template_guardrail_copy")
    require("ACTION PLATFORM V1" in css, "css_marker")

    result = {
        "ok": not failures,
        "contract": CONTRACT,
        "sections": sorted(snapshot.get("sections") or {}),
        "routes": sorted(REQUIRED_ROUTES),
        "registry": (capabilities.get("action_platform") or {}).get("state"),
        "roadmap": (roadmap.get("Action Platform") or {}).get("state"),
        "sentinel": sentinel.get("validation_result"),
        "guardrails": snapshot.get("guardrails"),
        "parallel_engine_absent": not (ROOT / "engines" / "action_platform_engine.py").exists(),
        "production_modified": False,
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if args.write_report:
        REPORT.write_text(_report(result, snapshot, sentinel), encoding="utf-8")
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
#!/usr/bin/env python3
"""Static and pure-runtime gate for SHARK Intelligence Platform."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.match_context_engine import build_match_context
from engines.sentinel_autopilot_engine import build_shark_intelligence_platform_contract_snapshot
from engines.shark_intelligence_platform_engine import (
    SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
    build_shark_intelligence_platform_snapshot,
    shark_intelligence_platform_snapshot,
)
from engines.sports_platform_contracts import build_sports_platform_contract_registry


def _module_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8").lstrip("\ufeff")
    tree = ast.parse(source)
    return {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }


def _match_context() -> dict:
    match = {
        "id": "m-shark-check-1",
        "match_id": "m-shark-check-1",
        "competition_id": "140",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "home_team": "Club Norte",
        "away_team": "Club Sur",
        "home_team_id": "club-norte",
        "away_team_id": "club-sur",
        "match_date": "2026-07-28",
        "kickoff_time": "20:30",
        "kickoff_iso": "2026-07-28T20:30:00+02:00",
        "status": "2H",
        "minute": 68,
        "home_score": 1,
        "away_score": 0,
        "score": "1-0",
        "source": "contract_check_fixture",
        "updated_at": "2026-07-28T21:58:00+02:00",
    }
    timeline = [
        {
            "id": "goal-1",
            "match_id": "m-shark-check-1",
            "elapsed": 12,
            "event_type": "Goal",
            "team_name": "Club Norte",
            "player_name": "Jugador Uno",
            "source": "contract_check_fixture",
        }
    ]
    return build_match_context(
        {"match": match, "timeline": timeline, "related_picks": []},
        madrid_context={
            "client_full_datetime_label": "martes, 28 de julio de 2026, 20:30",
            "machine_iso": "2026-07-28T20:30:00+02:00",
        },
        live_context={"provider": "contract_check_fixture", "updated_at": "2026-07-28T21:58:00+02:00", "events": timeline},
    )


def main() -> int:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    context = build_shark_intelligence_platform_snapshot(
        match_context=_match_context(),
        team_center={
            "contract": "TEAM-CENTER-PREMIUM-CLUB-EXPERIENCE-V1",
            "metrics": {"recent": 2, "upcoming": 1},
            "available_information": ["Forma reciente"],
            "missing_information": ["Fundacion no disponible."],
            "data_quality": {"state": "PARTIALLY_VERIFIED"},
            "sports_graph": {"edge_count": 4, "relationships": ["team_has_match"]},
            "no_fake_data": True,
        },
        competition_center={
            "contract": "COMPETITION-CENTER-LEAGUE-INTELLIGENCE-PLATFORM-V1",
            "metrics": {"teams": 4, "matches": 2},
            "available_information": ["Calendario"],
            "missing_information": ["Fase no disponible."],
            "data_quality": {"state": "PARTIALLY_VERIFIED"},
            "sports_graph": {"edge_count": 6, "relationships": ["competition_has_team"]},
            "no_fake_data": True,
        },
        sports_summary={"totals": {"today": 2, "live": 1}, "source": "sports_metrics_v1"},
        sports_metrics={"contract": "sports-metrics-v1"},
        observed_at_madrid="2026-07-28T22:00:00+02:00",
    )
    metadata = shark_intelligence_platform_snapshot()
    sentinel = build_shark_intelligence_platform_contract_snapshot(ROOT, "")
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    template = (ROOT / "templates" / "shark_intelligence_center.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    engine_imports = _module_imports(ROOT / "engines" / "shark_intelligence_platform_engine.py")

    require(context.get("contract") == SHARK_INTELLIGENCE_PLATFORM_CONTRACT, "contract")
    require(context.get("no_fake_data") is True, "no_fake_data")
    require(context.get("no_predictions") is True, "no_predictions")
    require(context["diagnostics"]["database_writes"] == 0, "database_writes")
    require(context["diagnostics"]["external_calls"] == 0, "external_calls")
    require(context["diagnostics"]["telegram_sends"] == 0, "telegram_sends")
    require(context["diagnostics"]["stripe_calls"] == 0, "stripe_calls")
    require(context["diagnostics"]["generative_ai_calls"] == 0, "generative_ai_calls")
    require(context["transparency"]["all_claims_traceable"] is True, "claims_traceable")
    require(len(context["claims"]) >= 4, "claims_count")
    require("match_center" in {item["key"] for item in context["modules"]}, "module_match_center")
    require("competition_center" in {item["key"] for item in context["modules"]}, "module_competition_center")
    require(metadata["guardrails"]["automatic_actions"] == 0, "metadata_no_automatic_actions")
    require((capabilities.get("shark_intelligence_platform") or {}).get("state") == "INTEGRATED", "registry")
    require(sentinel.get("validation_result") == "PASS", "sentinel_contract")
    require("data-shark-intelligence-contract" in template, "template_root")
    require("data-shark-intelligence-section=\"claims\"" in template, "template_claims")
    require("No hay conversacion IA" in template, "template_no_chat")
    require("SHARK INTELLIGENCE PLATFORM V1" in css, "css_marker")
    require(".shark-intelligence-v1" in css, "css_scope")
    require("build_shark_intelligence_page_context(" in app, "app_builder")
    require("@app.route(\"/shark-intelligence\")" in app, "route_page")
    require("@app.route(\"/api/shark/intelligence\")" in app, "route_api")
    require({"sqlite3", "requests", "urllib", "flask", "stripe"} & engine_imports == set(), "unsafe_imports")

    result = {
        "ok": not failures,
        "contract": SHARK_INTELLIGENCE_PLATFORM_CONTRACT,
        "claims": len(context.get("claims") or []),
        "modules": [item.get("key") for item in context.get("modules") or []],
        "sentinel": sentinel.get("validation_result"),
        "registry": (capabilities.get("shark_intelligence_platform") or {}).get("state"),
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Static and pure-runtime gate for Player Center Premium Sports Identity Platform."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.player_center_engine import PLAYER_CENTER_CONTRACT, build_player_center_context, player_center_snapshot
from engines.sentinel_autopilot_engine import build_player_center_experience_contract_snapshot
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_platform_contracts import build_sports_platform_contract_registry


def _match(match_id: str, status: str, *, date: str, score: str = "") -> dict:
    home_score = None
    away_score = None
    if "-" in score:
        left, right = score.split("-", 1)
        home_score = int(left)
        away_score = int(right)
    return {
        "id": match_id,
        "match_id": match_id,
        "external_id": match_id,
        "competition_id": "140",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "home_team": "Club Local",
        "away_team": "Union Norte" if status == "FT" else "Racing Este",
        "safe_home": "Club Local",
        "safe_away": "Union Norte" if status == "FT" else "Racing Este",
        "match_date": date,
        "kickoff_time": "20:30",
        "kickoff_iso": date + "T20:30:00+02:00",
        "status": status,
        "home_score": home_score,
        "away_score": away_score,
        "score": score,
        "source": "api_football_cache",
        "updated_at": date + "T22:30:00+02:00",
        "timeline": [
            {
                "id": match_id + "-goal-1",
                "match_id": match_id,
                "elapsed": 12,
                "event_type": "Goal",
                "team_name": "Club Local",
                "player_id": "101",
                "player_name": "Jugador Uno",
                "source": "api_football_cache",
            }
        ] if status == "FT" else [],
    }


def _detail() -> dict:
    return {
        "player": {
            "player_id": "101",
            "player_name": "Jugador Uno",
            "team_id": "club-local",
            "team_name": "Club Local",
            "position": "Delantero",
            "shirt_number": "9",
            "source": "api_football_cache",
        },
        "team": {
            "id": "club-local",
            "key": "club-local",
            "name": "Club Local",
            "official_name": "Club Local FC",
            "country": "Spain",
            "league": "Liga Real",
            "competition_id": "140",
            "source": "api_football_cache",
        },
        "competition": {
            "key": "liga-real",
            "external_id": "140",
            "name": "Liga Real",
            "country": "Spain",
            "season": "2026",
            "scope": "League",
            "source": "api_football_cache",
        },
        "matches": [
            _match("m-1", "FT", date="2026-07-20", score="2-0"),
            _match("m-2", "NS", date="2026-07-31"),
        ],
        "events": [
            {
                "id": "m-1-goal-1",
                "match_id": "m-1",
                "elapsed": 12,
                "event_type": "Goal",
                "team_name": "Club Local",
                "player_id": "101",
                "player_name": "Jugador Uno",
                "source": "api_football_cache",
            }
        ],
        "lineups": [
            {"fixture_id": "m-1", "player_id": "101", "player_name": "Jugador Uno", "team_name": "Club Local", "is_starting": 1}
        ],
        "injuries": [],
        "picks": [{"id": "pick-1", "match_id": "m-2", "selection": "Club Local", "odds": "1.80", "source": "picks"}],
    }


def _module_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8").lstrip("\ufeff")
    tree = ast.parse(source)
    return {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }


def main() -> int:
    failures: list[str] = []

    def require(condition: bool, message: str) -> None:
        if not condition:
            failures.append(message)

    context = build_player_center_context(_detail(), observed_at_madrid="2026-07-28T10:00:00+02:00")
    metadata = player_center_snapshot()
    sentinel = build_player_center_experience_contract_snapshot(ROOT, "")
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    template = (ROOT / "templates" / "player_detail.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    player_imports = _module_imports(ROOT / "engines" / "player_center_engine.py")
    graph_imports = _module_imports(ROOT / "engines" / "sports_graph_foundation_engine.py")

    require(context.get("contract") == PLAYER_CENTER_CONTRACT, "player_center_contract")
    require(context.get("sports_graph_contract") == SPORTS_GRAPH_FOUNDATION_CONTRACT, "sports_graph_contract")
    require(context.get("no_fake_data") is True, "no_fake_data")
    require(context["diagnostics"]["database_writes"] == 0, "database_writes")
    require(context["diagnostics"]["external_calls"] == 0, "external_calls")
    require(context["diagnostics"]["telegram_sends"] == 0, "telegram_sends")
    require(context["diagnostics"]["stripe_calls"] == 0, "stripe_calls")
    require(context["diagnostics"]["generative_ai_calls"] == 0, "generative_ai_calls")
    require(context["metrics"]["matches"] == 2, "matches")
    require(context["metrics"]["upcoming"] == 1, "upcoming")
    require(context["metrics"]["graph_edges"] > 0, "graph_edges")
    require("player_has_match" in context["sports_graph"]["relationships"], "graph_player_has_match")
    require("shark_context_mentions_player" in context["sports_graph"]["relationships"], "graph_shark_player")
    require("user_intelligence_observes_player" in context["sports_graph"]["relationships"], "graph_user_player")
    require("player-center-v1" in template, "template_root")
    require("match_card(match, true, true)" in template, "canonical_match_card")
    require("class=\"card match-card\"" not in template, "legacy_match_card_removed")
    require("PLAYER CENTER PREMIUM SPORTS IDENTITY PLATFORM V1" in css, "css_marker")
    require(".player-center-v1" in css, "css_scope")
    require("build_player_center_context(" in app, "app_integration")
    require(sentinel.get("validation_result") == "PASS", "sentinel_contract")
    require((capabilities.get("player_center") or {}).get("state") == "INTEGRATED", "registry_player_center")
    require({"sqlite3", "requests", "urllib", "flask", "stripe", "openai"} & player_imports == set(), "player_center_unsafe_imports")
    require({"sqlite3", "requests", "urllib", "flask", "stripe"} & graph_imports == set(), "sports_graph_unsafe_imports")
    require(metadata["guardrails"]["database_writes"] == 0, "metadata_no_db_writes")

    result = {
        "ok": not failures,
        "contract": PLAYER_CENTER_CONTRACT,
        "sports_graph_contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "metrics": context.get("metrics"),
        "relationships": context.get("sports_graph", {}).get("relationships"),
        "sentinel": sentinel.get("validation_result"),
        "registry_player_center": (capabilities.get("player_center") or {}).get("state"),
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())


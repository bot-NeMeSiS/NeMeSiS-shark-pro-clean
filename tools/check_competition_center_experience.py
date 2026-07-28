"""Static and pure-runtime gate for Competition Center Premium League Intelligence."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.competition_center_engine import (
    COMPETITION_CENTER_CONTRACT,
    build_competition_center_context,
    competition_center_snapshot,
)
from engines.sentinel_autopilot_engine import build_competition_center_experience_contract_snapshot
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_platform_contracts import build_sports_platform_contract_registry


def _match(match_id: str, home: str, away: str, status: str, *, date: str, score: str = "") -> dict:
    home_score = None
    away_score = None
    if "-" in score:
        left, right = score.split("-", 1)
        home_score = int(left)
        away_score = int(right)
    return {
        "id": match_id,
        "match_id": match_id,
        "competition_id": "140",
        "competition_key": "liga-real",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "round": "Jornada 12",
        "home_team": home,
        "away_team": away,
        "safe_home": home,
        "safe_away": away,
        "match_date": date,
        "kickoff_time": "20:30",
        "kickoff_iso": date + "T20:30:00+02:00",
        "status": status,
        "home_score": home_score,
        "away_score": away_score,
        "score": score,
        "source": "api_football_cache",
        "updated_at": date + "T22:30:00+02:00",
        "timeline": [{"id": match_id + "-goal", "match_id": match_id, "event_type": "Goal"}],
    }


def _detail() -> dict:
    return {
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
            _match("m-1", "Club Norte", "Club Sur", "FT", date="2026-07-20", score="2-0"),
            _match("m-2", "Club Este", "Club Oeste", "NS", date="2026-07-31"),
        ],
        "teams": [
            {"key": "club-norte", "name": "Club Norte", "country": "Spain", "league": "Liga Real", "source": "api_football_cache"},
            {"key": "club-sur", "name": "Club Sur", "country": "Spain", "league": "Liga Real", "source": "api_football_cache"},
        ],
        "standings": [
            {
                "rank": 1,
                "team_id": "club-norte",
                "team_name": "Club Norte",
                "played": 12,
                "goals_for": 24,
                "goals_against": 10,
                "points": 26,
                "form": "VVEVV",
                "description": "Champion",
                "source": "api_football_standings_deep",
            }
        ],
        "picks": [{"id": "pick-1", "match_id": "m-2", "selection": "Club Este", "odds": "1.90", "source": "picks"}],
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

    context = build_competition_center_context(_detail(), observed_at_madrid="2026-07-28T10:00:00+02:00")
    metadata = competition_center_snapshot()
    sentinel = build_competition_center_experience_contract_snapshot(ROOT, "")
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    template = (ROOT / "templates" / "competition_detail.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    competition_imports = _module_imports(ROOT / "engines" / "competition_center_engine.py")
    graph_imports = _module_imports(ROOT / "engines" / "sports_graph_foundation_engine.py")

    require(context.get("contract") == COMPETITION_CENTER_CONTRACT, "competition_center_contract")
    require(context.get("sports_graph_contract") == SPORTS_GRAPH_FOUNDATION_CONTRACT, "sports_graph_contract")
    require(context.get("no_fake_data") is True, "no_fake_data")
    require(context["diagnostics"]["database_writes"] == 0, "database_writes")
    require(context["diagnostics"]["external_calls"] == 0, "external_calls")
    require(context["diagnostics"]["telegram_sends"] == 0, "telegram_sends")
    require(context["diagnostics"]["stripe_calls"] == 0, "stripe_calls")
    require(context["metrics"]["matches"] == 2, "matches_metric")
    require(context["metrics"]["standings"] == 1, "standings_metric")
    require(context["metrics"]["graph_edges"] > 0, "graph_edges")
    require("competition_has_team" in context["sports_graph"]["relationships"], "graph_competition_has_team")
    require("pick_references_match" in context["sports_graph"]["relationships"], "graph_pick_references_match")
    require("competition-center-v1" in template, "template_root")
    require("match_card(match, true, true)" in template, "canonical_match_card")
    require("class=\"card match-card\"" not in template, "legacy_match_card_removed")
    require("No disponible" in template, "honest_empty_state")
    require("COMPETITION CENTER PREMIUM LEAGUE INTELLIGENCE V1" in css, "css_marker")
    require(".competition-center-v1" in css, "css_scope")
    require("build_competition_center_context(" in app, "app_integration")
    require(sentinel.get("validation_result") == "PASS", "sentinel_contract")
    require((capabilities.get("competition_center") or {}).get("state") == "INTEGRATED", "registry_competition_center")
    require((capabilities.get("sports_graph") or {}).get("state") == "INTEGRATED", "registry_sports_graph")
    require({"sqlite3", "requests", "urllib", "flask", "stripe"} & competition_imports == set(), "competition_center_unsafe_imports")
    require({"sqlite3", "requests", "urllib", "flask", "stripe"} & graph_imports == set(), "sports_graph_unsafe_imports")
    require(metadata["guardrails"]["database_writes"] == 0, "metadata_no_db_writes")

    result = {
        "ok": not failures,
        "contract": COMPETITION_CENTER_CONTRACT,
        "sports_graph_contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "metrics": context.get("metrics"),
        "relationships": context.get("sports_graph", {}).get("relationships"),
        "sentinel": sentinel.get("validation_result"),
        "registry_competition_center": (capabilities.get("competition_center") or {}).get("state"),
        "registry_sports_graph": (capabilities.get("sports_graph") or {}).get("state"),
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

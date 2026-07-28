"""Static and pure-runtime gate for Team Center Premium Club Experience."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.sentinel_autopilot_engine import build_team_center_experience_contract_snapshot
from engines.sports_graph_foundation_engine import SPORTS_GRAPH_FOUNDATION_CONTRACT
from engines.sports_platform_contracts import build_sports_platform_contract_registry
from engines.team_center_engine import TEAM_CENTER_CONTRACT, build_team_center_context, team_center_snapshot


def _match(match_id: str, home_score: int | None, away_score: int | None, *, date: str, opponent: str) -> dict:
    return {
        "id": match_id,
        "match_id": match_id,
        "competition_id": "140",
        "competition_name": "Liga Real",
        "league_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "home_team": "Club Local",
        "away_team": opponent,
        "safe_home": "Club Local",
        "safe_away": opponent,
        "match_date": date,
        "kickoff_time": "20:30",
        "kickoff_iso": date + "T20:30:00+02:00",
        "status": "FT" if home_score is not None else "NS",
        "home_score": home_score,
        "away_score": away_score,
        "score": f"{home_score}-{away_score}" if home_score is not None else "",
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
        ],
    }


def _detail() -> dict:
    return {
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
        "key": "club-local",
        "name": "Club Local",
        "identity": {"display_name": "Club Local", "crest_url": "/team-crest.svg?name=Club+Local"},
        "upcoming": [_match("m-4", None, None, date="2026-07-31", opponent="Racing Este")],
        "recent": [
            _match("m-1", 2, 0, date="2026-07-20", opponent="Union Norte"),
            _match("m-2", 1, 1, date="2026-07-17", opponent="Deportivo Centro"),
            _match("m-3", 0, 1, date="2026-07-13", opponent="Atletico Sur"),
        ],
        "live": [],
        "picks": [{"id": "pick-1", "match_id": "m-4", "selection": "Club Local", "odds": "1.80", "source": "picks"}],
        "is_favorite": False,
        "stats": {"upcoming": 1, "recent": 3, "live": 0, "picks": 1},
        "shark_context": "Contexto SHARK con datos reales cacheados.",
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

    context = build_team_center_context(_detail(), observed_at_madrid="2026-07-28T10:00:00+02:00")
    metadata = team_center_snapshot()
    sentinel = build_team_center_experience_contract_snapshot(ROOT, "")
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    template = (ROOT / "templates" / "team_detail.html").read_text(encoding="utf-8")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8")
    app = (ROOT / "app.py").read_text(encoding="utf-8")
    team_imports = _module_imports(ROOT / "engines" / "team_center_engine.py")
    graph_imports = _module_imports(ROOT / "engines" / "sports_graph_foundation_engine.py")

    require(context.get("contract") == TEAM_CENTER_CONTRACT, "team_center_contract")
    require(context.get("sports_graph_contract") == SPORTS_GRAPH_FOUNDATION_CONTRACT, "sports_graph_contract")
    require(context.get("no_fake_data") is True, "no_fake_data")
    require(context["diagnostics"]["database_writes"] == 0, "database_writes")
    require(context["diagnostics"]["external_calls"] == 0, "external_calls")
    require(context["diagnostics"]["telegram_sends"] == 0, "telegram_sends")
    require(context["diagnostics"]["stripe_calls"] == 0, "stripe_calls")
    require(context["form"]["sample_size"] == 3, "form_sample")
    require(context["metrics"]["graph_edges"] > 0, "graph_edges")
    require("match_has_team" in context["sports_graph"]["relationships"], "graph_match_has_team")
    require("pick_references_match" in context["sports_graph"]["relationships"], "graph_pick_references_match")
    require("team-center-v1" in template, "template_root")
    require("match_card(match, true, true)" in template, "canonical_match_card")
    require("class=\"card match-card\"" not in template, "legacy_match_card_removed")
    require("V540" not in template, "legacy_v540_removed")
    require("TEAM CENTER PREMIUM CLUB EXPERIENCE V1" in css, "css_marker")
    require(".team-center-v1" in css, "css_scope")
    require("build_team_center_context(" in app, "app_integration")
    require(sentinel.get("validation_result") == "PASS", "sentinel_contract")
    require((capabilities.get("team_center") or {}).get("state") == "INTEGRATED", "registry_team_center")
    require((capabilities.get("sports_graph") or {}).get("state") == "INTEGRATED", "registry_sports_graph")
    require({"sqlite3", "requests", "urllib", "flask", "stripe"} & team_imports == set(), "team_center_unsafe_imports")
    require({"sqlite3", "requests", "urllib", "flask", "stripe"} & graph_imports == set(), "sports_graph_unsafe_imports")
    require(metadata["guardrails"]["database_writes"] == 0, "metadata_no_db_writes")

    result = {
        "ok": not failures,
        "contract": TEAM_CENTER_CONTRACT,
        "sports_graph_contract": SPORTS_GRAPH_FOUNDATION_CONTRACT,
        "metrics": context.get("metrics"),
        "relationships": context.get("sports_graph", {}).get("relationships"),
        "sentinel": sentinel.get("validation_result"),
        "registry_team_center": (capabilities.get("team_center") or {}).get("state"),
        "registry_sports_graph": (capabilities.get("sports_graph") or {}).get("state"),
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
"""Static and pure-runtime gate for SPORTS-KNOWLEDGE-LAYER-V1."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from engines.match_context_engine import build_match_context
from engines.sentinel_autopilot_engine import (
    build_v944_match_center_foundation_contract_snapshot,
)
from engines.sports_domain_model_engine import SPORTS_DOMAIN_MODEL_CONTRACT, build_unified_domain_snapshot
from engines.sports_knowledge_layer_engine import (
    COMPETITION_KNOWLEDGE_CONTRACT,
    MATCH_KNOWLEDGE_CONTRACT,
    SEASON_KNOWLEDGE_CONTRACT,
    SPORTS_KNOWLEDGE_CONSUMERS,
    SPORTS_KNOWLEDGE_LAYER_CONTRACT,
    TEAM_KNOWLEDGE_CONTRACT,
    build_sports_knowledge_snapshot,
    sports_knowledge_layer_snapshot,
)


def _match() -> dict:
    return {
        "id": "sports-knowledge-check-1",
        "external_id": "991",
        "sport_key": "soccer",
        "competition_id": "140",
        "competition_name": "Liga Real",
        "country": "Spain",
        "season": "2026",
        "round": "Jornada 10",
        "home_team_id": "10",
        "away_team_id": "20",
        "home_team": "Club Local",
        "away_team": "Union Visitante",
        "kickoff_iso": "2026-07-26T20:30:00+02:00",
        "status": "LIVE",
        "minute": 68,
        "home_score": 1,
        "away_score": 0,
        "score": "1-0",
        "source": "api_football",
        "updated_at": "2026-07-26T21:58:00+02:00",
    }


def _events() -> list[dict]:
    return [
        {
            "id": "goal-1",
            "elapsed": 12,
            "event_type": "Goal",
            "detail": "Normal Goal",
            "team_name": "Club Local",
            "player_id": "101",
            "player_name": "Jugador Uno",
            "source": "api_football",
            "captured_at": "2026-07-26T21:58:00+02:00",
        }
    ]


def _module_imports(path: Path) -> set[str]:
    source = path.read_text(encoding="utf-8")
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

    module_path = ROOT / "engines" / "sports_knowledge_layer_engine.py"
    module_source = module_path.read_text(encoding="utf-8")
    metadata = sports_knowledge_layer_snapshot()
    domain = build_unified_domain_snapshot(
        _match(),
        live_context={
            "provider": "api_football",
            "updated_at": "2026-07-26T21:58:00+02:00",
            "events": _events(),
        },
        timeline_events=_events(),
        now_madrid="2026-07-26T22:00:00+02:00",
    )
    snapshot = build_sports_knowledge_snapshot(
        domain_model=domain,
        timeline_events=domain["timeline_events"],
        now_madrid="2026-07-26T22:00:00+02:00",
    )
    context = build_match_context(
        {"match": _match(), "related_picks": []},
        madrid_context={
            "client_full_datetime_label": "domingo, 26 de julio - 20:30",
            "client_date_label": "domingo, 26 de julio",
            "client_time_label": "20:30",
        },
        live_context={
            "provider": "api_football",
            "updated_at": "2026-07-26T21:58:00+02:00",
            "events": _events(),
        },
    )
    sentinel = build_v944_match_center_foundation_contract_snapshot(ROOT, "")
    imports = _module_imports(module_path)

    require(metadata.get("contract") == SPORTS_KNOWLEDGE_LAYER_CONTRACT, "metadata_contract")
    require(snapshot.get("contract") == SPORTS_KNOWLEDGE_LAYER_CONTRACT, "snapshot_contract")
    require(snapshot.get("source_domain_contract") == SPORTS_DOMAIN_MODEL_CONTRACT, "source_domain_contract")
    require(snapshot["match_knowledge"]["contract"] == MATCH_KNOWLEDGE_CONTRACT, "match_knowledge_contract")
    require(snapshot["team_knowledge"]["home"]["contract"] == TEAM_KNOWLEDGE_CONTRACT, "team_knowledge_contract")
    require(snapshot["competition_knowledge"]["contract"] == COMPETITION_KNOWLEDGE_CONTRACT, "competition_contract")
    require(snapshot["season_knowledge"]["contract"] == SEASON_KNOWLEDGE_CONTRACT, "season_contract")
    require(set(snapshot["future_consumers"]) == set(SPORTS_KNOWLEDGE_CONSUMERS), "future_consumers")
    require(snapshot["diagnostics"]["database_writes"] == 0, "database_writes")
    require(snapshot["diagnostics"]["external_calls"] == 0, "external_calls")
    require(snapshot["diagnostics"]["telegram_sends"] == 0, "telegram_sends")
    require(snapshot["diagnostics"]["stripe_calls"] == 0, "stripe_calls")
    require(snapshot["diagnostics"]["single_domain_snapshot"] is True, "single_domain_snapshot")
    require(context["sports_knowledge"]["contract"] == SPORTS_KNOWLEDGE_LAYER_CONTRACT, "match_context_embeds_knowledge")
    require(context["diagnostics"]["sports_knowledge_database_writes"] == 0, "match_context_no_writes")
    require(context["diagnostics"]["sports_knowledge_external_calls"] == 0, "match_context_no_external_calls")
    require(sentinel["validation_result"] == "PASS", "sentinel_contract")
    require({"sqlite3", "requests", "urllib", "flask", "stripe"} & imports == set(), "unsafe_imports")
    require("TELEGRAM_BOT_TOKEN" not in module_source, "telegram_secret_literal")
    require("STRIPE_SECRET_KEY" not in module_source, "stripe_secret_literal")
    require("OPENAI_API_KEY" not in module_source, "openai_secret_literal")

    result = {
        "ok": not failures,
        "contract": SPORTS_KNOWLEDGE_LAYER_CONTRACT,
        "source_domain_contract": snapshot.get("source_domain_contract"),
        "future_consumers": list(SPORTS_KNOWLEDGE_CONSUMERS),
        "guardrails": snapshot.get("diagnostics"),
        "sentinel": sentinel.get("validation_result"),
        "failures": failures,
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

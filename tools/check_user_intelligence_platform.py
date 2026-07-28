from __future__ import annotations

import ast
import inspect
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import engines.user_intelligence_platform_engine as user_platform_module
from engines.sentinel_autopilot_engine import build_user_intelligence_platform_contract_snapshot
from engines.user_intelligence_platform_engine import (
    USER_INTELLIGENCE_PLATFORM_CONTRACT,
    build_user_intelligence_platform_snapshot,
    sanitize_user_intelligence_preferences,
)
from engines.sports_platform_contracts import build_sports_platform_contract_registry



def _activity() -> list[dict]:
    return [
        {
            "activity_type": "view",
            "target_type": "match",
            "target_id": "match-qa",
            "payload": {
                "match_title": "Club Norte vs Club Sur",
                "home_team": "Club Norte",
                "away_team": "Club Sur",
                "competition_name": "Liga Real",
                "lane": "today",
            },
            "created_at": "2026-07-28T21:00:00+02:00",
        },
        {
            "activity_type": "view",
            "target_type": "team",
            "target_id": "club-norte",
            "payload": {"team_name": "Club Norte"},
            "created_at": "2026-07-28T21:05:00+02:00",
        },
    ]


def _favorites() -> list[dict]:
    return [
        {"kind": "team", "value": "club-norte", "label": "Club Norte"},
        {"kind": "league", "value": "liga-real", "label": "Liga Real"},
    ]


def main() -> int:
    failures: list[str] = []

    def require(condition: bool, name: str) -> None:
        if not condition:
            failures.append(name)

    preferences = sanitize_user_intelligence_preferences(action="enable", observed_at_madrid="2026-07-28T22:00:00+02:00")
    snapshot = build_user_intelligence_platform_snapshot(
        user={"id": "qa-user", "membership": "PRO"},
        activity=_activity(),
        favorites=_favorites(),
        preferences=preferences,
        shark_intelligence={"contract": "SHARK-INTELLIGENCE-PLATFORM-V1"},
        observed_at_madrid="2026-07-28T22:00:00+02:00",
    )
    registry = build_sports_platform_contract_registry(ROOT)
    capabilities = {item["key"]: item for item in registry.get("capabilities") or []}
    template = (ROOT / "templates" / "user_intelligence_center.html").read_text(encoding="utf-8", errors="replace")
    css = (ROOT / "static" / "v933-product.css").read_text(encoding="utf-8", errors="replace")
    app_py = (ROOT / "app.py").read_text(encoding="utf-8", errors="replace")
    sentinel = build_user_intelligence_platform_contract_snapshot(ROOT, "")
    source = inspect.getsource(user_platform_module)
    tree = ast.parse(source)
    imported_roots = {
        alias.name.split(".", 1)[0]
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }

    require(snapshot["contract"] == USER_INTELLIGENCE_PLATFORM_CONTRACT, "contract")
    require(snapshot["privacy"]["controls"]["delete_profile"] is True, "delete_profile_control")
    require(snapshot["privacy"]["controls"]["disable_personalization"] is True, "disable_control")
    require(snapshot["privacy"]["data_leaves_nemesis"] is False, "no_external_data")
    require(snapshot["personalization"]["automatic_home_personalization"] is False, "no_auto_home")
    require(snapshot["diagnostics"]["external_calls"] == 0, "no_external_calls")
    require(snapshot["diagnostics"]["telegram_sends"] == 0, "no_telegram")
    require(snapshot["diagnostics"]["stripe_calls"] == 0, "no_stripe")
    require(snapshot["diagnostics"]["database_writes_by_get"] == 0, "no_get_writes")
    require(snapshot["signals"]["teams"], "teams_signal")
    require(snapshot["signals"]["competitions"], "competitions_signal")
    require((capabilities.get("user_intelligence_platform") or {}).get("state") == "INTEGRATED", "registry")
    require("data-user-intelligence-contract" in template, "template_contract")
    require("data-user-privacy-contract" in template, "privacy_contract")
    require("Borrar perfil" in template, "delete_copy")
    require("data-user-privacy-control=\"delete\"" in template, "delete_control_marker")
    require("No cambia la Home automaticamente" in template, "no_auto_home_copy")
    require("USER INTELLIGENCE PLATFORM V1" in css, "css_contract")
    require("@app.route(\"/user-intelligence\")" in app_py, "page_route")
    require("@app.route(\"/api/user-intelligence/summary\")" in app_py, "summary_api")
    require("@app.route(\"/api/user-intelligence/preferences\", methods=[\"POST\"])" in app_py, "preferences_api")
    require(sentinel["validation_result"] == "PASS", "sentinel_contract")
    require({"sqlite3", "requests", "urllib", "flask", "stripe", "openai"} & imported_roots == set(), "pure_engine_imports")
    require("TELEGRAM_BOT_TOKEN" not in source, "no_telegram_secret")
    require("STRIPE_SECRET_KEY" not in source, "no_stripe_secret")
    require("OPENAI_API_KEY" not in source, "no_openai_secret")

    payload = {
        "ok": not failures,
        "contract": snapshot["contract"],
        "privacy_contract": snapshot["privacy_contract"],
        "registry": (capabilities.get("user_intelligence_platform") or {}).get("state"),
        "sentinel": sentinel["validation_result"],
        "signals": snapshot["metrics"],
        "failures": failures,
    }
    print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())

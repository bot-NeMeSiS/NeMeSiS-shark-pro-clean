"""Deterministic checks for engines.match_live_story_engine."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from engines.match_live_story_engine import build_match_live_story, normalize_story_events


match = {
    "id": "match-1",
    "home_team": "Real Betis",
    "away_team": "Sevilla FC",
    "status": "live",
    "minute": 67,
}

events = [
    {
        "id": "event-3",
        "type": "yellow card",
        "minute": 66,
        "team": "Sevilla FC",
        "player": "Jugador C",
        "source": "provider-cache",
    },
    {
        "id": "event-1",
        "type": "goal",
        "minute": "12",
        "team": "Real Betis",
        "player": "Jugador A",
        "source": "provider-cache",
    },
    {
        "id": "event-2",
        "type": "var",
        "minute": "14+1",
        "team": "Real Betis",
        "source": "provider-cache",
        "detail": "Revision confirmada por el proveedor",
    },
    {
        "id": "event-2",
        "type": "var",
        "minute": "14+1",
        "team": "Real Betis",
        "source": "provider-cache",
    },
    {
        "id": "event-4",
        "type": "provider-special-event",
        "minute": 67,
        "source": "provider-cache",
    },
    {
        "id": "invalid-no-source",
        "type": "goal",
        "minute": 70,
    },
]

errors: list[str] = []
normalized = normalize_story_events(events, match)

if [item["id"] for item in normalized] != ["event-1", "event-2", "event-3", "event-4"]:
    errors.append("events_not_sorted_or_deduplicated")
if normalized[1]["minute_label"] != "14+1'":
    errors.append("added_time_not_normalized")
if normalized[-1]["type"] != "unknown":
    errors.append("unknown_event_not_preserved_safely")
if normalized[-1]["headline"] != "Evento confirmado":
    errors.append("unknown_event_invented_detail")

story = build_match_live_story(
    match,
    events,
    generated_at=datetime(2026, 7, 24, 12, 0, tzinfo=timezone.utc),
)

if story["contract"] != "MATCH-CENTER-LIFECYCLE-STORY-V1":
    errors.append("contract_missing")
if story["state"] != "story_available":
    errors.append("story_not_available")
if story["counts"] != {"events": 4, "cycles": 2, "key_events": 2}:
    errors.append(f"unexpected_counts:{story['counts']}")
if story["cycles"][0]["event_count"] != 2 or story["cycles"][1]["event_count"] != 2:
    errors.append("event_cycles_not_grouped")
if story["latest_event"]["id"] != "event-4":
    errors.append("latest_event_wrong")
if story["momentum_available"] or story["sporting_consequences_available"]:
    errors.append("unsupported_intelligence_claimed")
if not story["no_fake_data"] or not story["no_external_calls"] or not story["no_database_writes"]:
    errors.append("safety_contract_missing")

empty_story = build_match_live_story(match, [])
if empty_story["state"] != "waiting_for_confirmed_events":
    errors.append("empty_story_not_safe")
if empty_story["timeline"] or empty_story["cycles"]:
    errors.append("empty_story_contains_events")

invalid_story = build_match_live_story({}, events)
if invalid_story["state"] != "invalid_match_context":
    errors.append("invalid_context_not_blocked")

if errors:
    raise SystemExit("MATCH_LIVE_STORY_ENGINE_FAIL: " + ", ".join(errors))

print("MATCH_LIVE_STORY_ENGINE_OK")

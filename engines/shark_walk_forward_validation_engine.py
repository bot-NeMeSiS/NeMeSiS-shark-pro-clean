"""Read-only chronological diagnostics for SHARK football forecast research.

This evaluator is intentionally not a pick generator and never writes to the
application database. It evaluates a simple Elo reference against a
competition-frequency baseline. Results are diagnostic only and cannot certify
or publish a SHARK forecast.
"""

from __future__ import annotations

import math
import re
import sqlite3
import unicodedata
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any

from engines.shark_prediction_engine import _finished_matches


CONTRACT = "SHARK_WALK_FORWARD_DIAGNOSTIC_V1"
TERMINAL_ONLY_POLICY = (
    "Only explicitly finished matches with valid integer scores are considered. "
    "All fixtures on a date are evaluated before that date's results update ratings."
)
NOT_FOR_CUSTOMER = (
    "This is an offline diagnostic, not a calibrated SHARK forecast or betting recommendation."
)


def _normalized_key(value: Any) -> str:
    text = str(value or "").strip().casefold()
    text = "".join(
        char for char in unicodedata.normalize("NFKD", text)
        if not unicodedata.combining(char)
    )
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _bounded_int(value: Any, default: int, low: int, high: int) -> int:
    try:
        return max(low, min(high, int(value)))
    except (TypeError, ValueError, OverflowError):
        return default


def _bounded_float(value: Any, default: float, low: float, high: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return max(low, min(high, parsed)) if math.isfinite(parsed) else default


def _team_key(row: dict[str, Any], side: str) -> str:
    identifier = row.get(f"{side}_team_id")
    if identifier not in (None, ""):
        return f"id:{str(identifier).strip().casefold()}"
    label = _normalized_key(row.get(f"{side}_team"))
    return f"name:{label}" if label else ""


def _competition_key(row: dict[str, Any]) -> str:
    for field in ("competition_id", "competition_key", "competition_name", "league_name"):
        value = row.get(field)
        if value not in (None, ""):
            normalized = _normalized_key(value)
            if normalized:
                return f"competition:{normalized}"
    return ""


def _match_day(row: dict[str, Any]) -> date | None:
    raw = str(row.get("match_date") or row.get("kickoff_iso") or "").strip()
    if not raw:
        return None
    try:
        # Database match_date is the app's fixture-local calendar date. When it
        # is absent, the ISO kickoff prefix still gives a conservative day key.
        return date.fromisoformat(raw[:10])
    except (TypeError, ValueError):
        return None


def _canonical_fixtures(rows: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], int, int]:
    """Deduplicate provider copies and discard conflicting same-fixture rows."""
    grouped: dict[tuple[str, date, str, str], list[dict[str, Any]]] = defaultdict(list)
    excluded_rows = 0
    for row in rows:
        day = _match_day(row)
        competition = _competition_key(row)
        home = _team_key(row, "home")
        away = _team_key(row, "away")
        if day is None or not competition or not home or not away or home == away:
            excluded_rows += 1
            continue
        pair = tuple(sorted((home, away)))
        grouped[(competition, day, pair[0], pair[1])].append(row)

    fixtures: list[dict[str, Any]] = []
    duplicate_count = 0
    for (competition, day, _first, _second), copies in grouped.items():
        outcomes_by_orientation = set()
        for row in copies:
            home = _team_key(row, "home")
            away = _team_key(row, "away")
            home_score = int(row["_home_score"])
            away_score = int(row["_away_score"])
            outcomes_by_orientation.add((home, away, home_score, away_score))
        canonical_scores = {
            tuple(sorted(((home, home_score), (away, away_score))))
            for home, away, home_score, away_score in outcomes_by_orientation
        }
        if len(canonical_scores) != 1:
            excluded_rows += len(copies)
            continue
        selected = min(copies, key=lambda item: str(item.get("id") or item.get("external_id") or ""))
        selected = dict(selected)
        selected["_validation_day"] = day
        selected["_validation_competition"] = competition
        selected["_validation_home_key"] = _team_key(selected, "home")
        selected["_validation_away_key"] = _team_key(selected, "away")
        fixtures.append(selected)
        duplicate_count += max(0, len(copies) - 1)

    fixtures.sort(key=lambda item: (
        item["_validation_day"], item["_validation_competition"],
        item["_validation_home_key"], item["_validation_away_key"],
        str(item.get("id") or ""),
    ))
    return fixtures, duplicate_count, excluded_rows


def _elo_home_probability(home_elo: float, away_elo: float, home_advantage: float) -> float:
    exponent = max(-12.0, min(12.0, -(home_elo + home_advantage - away_elo) / 400.0))
    return 1.0 / (1.0 + 10.0 ** exponent)


def _probabilities(
    home_elo: float,
    away_elo: float,
    home_advantage: float,
    draw_count: int,
    competition_matches: int,
) -> tuple[float, float, float]:
    # A conservative 25% prior is shrunk by historical draws from prior days.
    draw_probability = (draw_count + 2.5) / (competition_matches + 10.0)
    draw_probability = max(0.05, min(0.55, draw_probability))
    home_given_decision = _elo_home_probability(home_elo, away_elo, home_advantage)
    return (
        (1.0 - draw_probability) * home_given_decision,
        draw_probability,
        (1.0 - draw_probability) * (1.0 - home_given_decision),
    )


def _metrics(rows: list[tuple[tuple[float, float, float], int]]) -> dict[str, Any] | None:
    if not rows:
        return None
    brier_total = 0.0
    log_loss_total = 0.0
    correct = 0
    for probabilities, actual in rows:
        target = tuple(1.0 if index == actual else 0.0 for index in range(3))
        brier_total += sum((probability - value) ** 2 for probability, value in zip(probabilities, target))
        log_loss_total -= math.log(max(1e-12, min(1.0, probabilities[actual])))
        correct += int(max(range(3), key=lambda index: probabilities[index]) == actual)
    count = len(rows)
    return {
        "sample_size": count,
        "brier_score": round(brier_total / count, 6),
        "log_loss": round(log_loss_total / count, 6),
        "top_outcome_accuracy_pct": round(correct * 100.0 / count, 3),
    }


def evaluate_shark_walk_forward(
    db_path: str,
    *,
    min_history_matches_per_team: int = 5,
    min_review_sample: int = 100,
    max_matches: int = 10000,
    elo_k_factor: float = 20.0,
    home_advantage: float = 55.0,
) -> dict[str, Any]:
    """Evaluate an Elo reference on past fixtures without modifying SQLite.

    Each test day is scored using only data from earlier days. Same-day results
    are applied after every prediction for that day has been calculated. The
    returned metrics are for diagnostics only, regardless of sample size.
    """
    try:
        path = Path(db_path).resolve()
        if not path.is_file():
            return _empty("DATABASE_NOT_FOUND")
        conn = sqlite3.connect(path.as_uri() + "?mode=ro", uri=True, timeout=5)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA query_only=ON")
    except (OSError, sqlite3.Error, ValueError):
        return _empty("DATABASE_UNAVAILABLE")

    try:
        source_rows = _finished_matches(conn, _bounded_int(max_matches, 10000, 1, 100000))
    finally:
        conn.close()

    if not source_rows:
        return _empty("NO_FINISHED_MATCHES")
    fixtures, duplicates, excluded = _canonical_fixtures(source_rows)
    if not fixtures:
        result = _empty("NO_VALID_DATED_MATCHES")
        result["matches_read"] = len(source_rows)
        result["duplicate_rows_collapsed"] = duplicates
        result["incomplete_or_conflicting_rows_excluded"] = excluded
        return result

    min_history = _bounded_int(min_history_matches_per_team, 5, 1, 1000)
    review_sample = _bounded_int(min_review_sample, 100, 1, 100000)
    k_factor = _bounded_float(elo_k_factor, 20.0, 0.0, 100.0)
    home_edge = _bounded_float(home_advantage, 55.0, -300.0, 300.0)
    elo: dict[tuple[str, str], float] = defaultdict(lambda: 1500.0)
    team_counts: dict[tuple[str, str], int] = defaultdict(int)
    competition_outcomes: dict[str, list[int]] = defaultdict(lambda: [0, 0, 0])
    model_rows: list[tuple[tuple[float, float, float], int]] = []
    baseline_rows: list[tuple[tuple[float, float, float], int]] = []
    eligible_fixtures = 0
    days = defaultdict(list)
    for fixture in fixtures:
        days[fixture["_validation_day"]].append(fixture)

    for day in sorted(days):
        day_updates: list[tuple[str, str, str, str, int, float]] = []
        for fixture in days[day]:
            competition = fixture["_validation_competition"]
            home = fixture["_validation_home_key"]
            away = fixture["_validation_away_key"]
            home_state = (competition, home)
            away_state = (competition, away)
            home_score = int(fixture["_home_score"])
            away_score = int(fixture["_away_score"])
            actual = 0 if home_score > away_score else 1 if home_score == away_score else 2
            home_elo = elo[home_state]
            away_elo = elo[away_state]
            previous = competition_outcomes[competition]
            previous_count = sum(previous)
            baseline = tuple((count + 1.0) / (previous_count + 3.0) for count in previous)
            baseline_rows.append((baseline, actual))
            if team_counts[home_state] >= min_history and team_counts[away_state] >= min_history:
                model_rows.append((
                    _probabilities(home_elo, away_elo, home_edge, previous[1], previous_count),
                    actual,
                ))
                eligible_fixtures += 1
            expected_home = _elo_home_probability(home_elo, away_elo, home_edge)
            actual_home = 1.0 if home_score > away_score else 0.5 if home_score == away_score else 0.0
            day_updates.append((competition, home, away, actual, expected_home, actual_home))

        for competition, home, away, actual, expected_home, actual_home in day_updates:
            home_state = (competition, home)
            away_state = (competition, away)
            delta = k_factor * (actual_home - expected_home)
            elo[home_state] += delta
            elo[away_state] -= delta
            team_counts[home_state] += 1
            team_counts[away_state] += 1
            competition_outcomes[competition][actual] += 1

    model_metrics = _metrics(model_rows)
    baseline_metrics = _metrics(baseline_rows)
    state = "REVIEWABLE_DIAGNOSTIC" if eligible_fixtures >= review_sample else "INSUFFICIENT_EVALUATION_SAMPLE"
    return {
        "contract": CONTRACT,
        "state": state,
        "diagnostic_only": True,
        "validated_for_customer": False,
        "read_only": True,
        "matches_read": len(source_rows),
        "dated_unique_matches": len(fixtures),
        "duplicate_rows_collapsed": duplicates,
        "incomplete_or_conflicting_rows_excluded": excluded,
        "eligible_model_evaluations": eligible_fixtures,
        "competition_baseline_evaluations": len(baseline_rows),
        "minimum_history_matches_per_team": min_history,
        "minimum_review_sample": review_sample,
        "method": "Elo reference with prior-day-only updates; smoothed draw prior; comparison against prior competition outcome frequency.",
        "temporal_policy": TERMINAL_ONLY_POLICY,
        "model_reference": model_metrics,
        "competition_frequency_baseline": baseline_metrics,
        "limitations": [NOT_FOR_CUSTOMER, "No pick, confidence label, or profitability claim is generated."],
    }


def _empty(state: str) -> dict[str, Any]:
    return {
        "contract": CONTRACT,
        "state": state,
        "diagnostic_only": True,
        "validated_for_customer": False,
        "read_only": True,
        "matches_read": 0,
        "dated_unique_matches": 0,
        "duplicate_rows_collapsed": 0,
        "incomplete_or_conflicting_rows_excluded": 0,
        "eligible_model_evaluations": 0,
        "competition_baseline_evaluations": 0,
        "model_reference": None,
        "competition_frequency_baseline": None,
        "limitations": [NOT_FOR_CUSTOMER],
    }

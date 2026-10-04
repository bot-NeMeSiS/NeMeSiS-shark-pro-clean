"""Field-level sports truth over receipts already acquired by NeMeSiS.

No network, credentials, AI, or implicit database commits. Raw receipts remain
separate from decisions. The SQLite repository is a separate module; this engine
only resolves already acquired evidence and owns a bounded in-memory cache.
"""
from __future__ import annotations

from engines.snapshot_copy_engine import clone_snapshot
from collections import OrderedDict
from datetime import datetime, timezone, timedelta
import hashlib
import json
import math
import re
import threading
from zoneinfo import ZoneInfo

from engines.v935_launch_trust_engine import match_status_truth, match_kickoff_madrid, LIVE_STALE_SECONDS

CONTRACT = "NEMESIS-UNIFIED-SPORTS-TRUTH-V1"
MADRID = ZoneInfo("Europe/Madrid")
GROUPS = {
    "identity": ("home_team", "away_team", "home_team_id", "away_team_id", "competition_id", "competition_name", "league_name", "country", "home_logo", "away_logo", "venue", "season", "round"),
    "kickoff": ("kickoff_iso",),
    "state": ("status", "home_score", "away_score", "score", "minute"),
    "lineups": ("lineups",), "stats": ("stats",), "events": ("events",),
    "players": ("players",), "injuries": ("injuries",),
    "standings": ("standings",), "h2h": ("h2h",),
    "video": ("video",), "odds": ("odds_h2h_json", "bookmaker"),
}
FOOTBALL = ("api_football", "thesportsdb", "local_cache", "the_odds_api")
IDENTITY = ("thesportsdb", "api_football", "local_cache", "the_odds_api")
PRECEDENCE = {field: (IDENTITY if group in {"identity", "video"} else
                      ("the_odds_api",) if group == "odds" else FOOTBALL)
              for group, fields in GROUPS.items() for field in fields}
TTL = {"identity": 30 * 86400, "kickoff": 86400, "state": LIVE_STALE_SECONDS,
       "lineups": 86400, "stats": LIVE_STALE_SECONDS, "events": LIVE_STALE_SECONDS, "players": 86400,
       "injuries": 86400, "standings": 86400, "h2h": 7 * 86400,
       "video": 30 * 86400, "odds": 900}
UNAVAILABLE = {"BLOCKED_BY_ACCESS", "PLAN_RESTRICTED", "TECHNICAL_ERROR", "UNRESOLVED_IDENTITY", "UNAVAILABLE", "NOT_REQUESTED"}
ABSENCE = {"NO_STATISTICS", "NO_VIDEO", "NO_LINEUPS", "EMPTY_CONFIRMED"}
_RESOLVED_CACHE = OrderedDict()
_CACHE_LOCK = threading.RLock()


def _safe_raw(value):
    if isinstance(value, dict):
        return {k: _safe_raw(v) for k, v in value.items() if not re.search(r"password|secret|token|authorization|api.?key|headers", str(k), re.I)}
    if isinstance(value, list):
        return [_safe_raw(v) for v in value]
    return value


def provider_name(value):
    value = str(value or "").lower().replace("-", "_")
    if "football" in value or "api_sports" in value:
        return "api_football"
    if "sportsdb" in value:
        return "thesportsdb"
    if "odds" in value:
        return "the_odds_api"
    return "local_cache"


def instant(value):
    if isinstance(value, datetime):
        dt = value
    else:
        try:
            dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    # Existing ingest clocks use UTC without an offset. Generic updated_at is
    # intentionally never accepted as an observation clock.
    return (dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt).astimezone(timezone.utc)


def _json(value):
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value or "{}")
    except (ValueError, TypeError):
        return {}


def _present(value):
    return value is not None and value != ""


def _score(value):
    if type(value) is bool or value in (None, ""):
        return None
    text = str(value)
    return int(text) if re.fullmatch(r"\d{1,2}", text) else None


def evidence_from_row(row, *, provider=None, fetched_at=None):
    """Adapt a normalized persisted provider row, never its generic write clock."""
    data = dict(row)
    raw = _json(data.get("raw_json") or data.get("payload_json"))
    raw = _safe_raw(raw) if isinstance(raw, dict) else {}
    stamp = next((data.get(k) for k in ("live_updated_at", "provider_updated_at", "last_synced_at", "source_timestamp") if data.get(k)), None)
    source = provider_name(provider or data.get("source") or data.get("provider"))
    values = {key: clone_snapshot(data.get(key)) for fields in GROUPS.values() for key in fields if key in data}
    values["status"] = data.get("status_short") or data.get("provider_status") or data.get("status")
    values["minute"] = data.get("minute") if _present(data.get("minute")) else data.get("elapsed")
    values["competition_id"] = data.get("competition_id") or data.get("league_id")
    values["competition_name"] = data.get("competition_name") or data.get("league_name")
    values["round"] = data.get("round") or data.get("round_name")
    for key in ("home_score", "away_score"):
        values[key] = _score(values.get(key))
    if values["home_score"] is None or values["away_score"] is None:
        pair = re.fullmatch(r"(\d{1,2})\s*[-:]\s*(\d{1,2})", str(values.get("score") or ""))
        if pair:
            values["home_score"], values["away_score"] = map(int, pair.groups())
    for group in ("lineups", "stats", "events", "players", "injuries", "standings", "h2h", "video"):
        if group not in values and group in raw:
            values[group] = clone_snapshot(raw[group])
    kickoff = match_kickoff_madrid(data)
    if kickoff:
        values["kickoff_iso"] = kickoff.astimezone(timezone.utc).isoformat()
    # Preserve conflicting status signals within a single receipt for fail-closed
    # lifecycle handling; cross-provider conflicts are resolved separately.
    truth = match_status_truth({**data, **values})
    values["_status_conflict"] = truth.get("status_conflict", False)
    coverage = data.get("coverage") or raw.get("coverage") or {}
    coverage = coverage if isinstance(coverage, dict) else {}
    clocks = {group: {"observed_at": stamp, "fetched_at": fetched_at or data.get("fetched_at") or stamp,
                      "source": str(data.get("source") or source), "provider": source,
                      "state": coverage.get(group, "AVAILABLE"),
                      "match_status_at_receipt": data.get("context_status") or values.get("status")}
              for group in GROUPS}
    for group in GROUPS:
        if isinstance(clocks[group]["state"], dict):
            descriptor = clocks[group]["state"]
            clocks[group]["state"] = descriptor.get("state") or descriptor.get("status") or ("UNAVAILABLE" if descriptor.get("available") is False else "AVAILABLE")
            for key in ("observed_at", "fetched_at"):
                if descriptor.get(key):
                    clocks[group][key] = descriptor[key]
        if group in {"state", "stats", "events"} and (data.get("is_stale") or data.get("stale")):
            clocks[group]["state"] = "STALE"
        clock = data.get(f"{group}_observed_at") or raw.get(f"{group}_observed_at")
        if clock:
            clocks[group]["observed_at"] = clock
    odds_raw = _json(values.get("odds_h2h_json"))
    odds_source = odds_raw.get("source") if isinstance(odds_raw, dict) else None
    if data.get("odds_updated_at") and (odds_source == "The Odds API" or source == "the_odds_api"):
        clocks["odds"].update(observed_at=data["odds_updated_at"], fetched_at=data.get("odds_fetched_at") or data.get("fetched_at") or odds_raw.get("fetched_at"), provider="the_odds_api", source="the_odds_api")
    else:
        clocks["odds"].update(observed_at=None, fetched_at=None)
    values["_status_signals"] = {k: data.get(k, raw.get(k)) for k in ("strStatus", "strProgress", "progress", "provider_status", "status_short", "match_status", "fixture_status") if k in data or k in raw}
    return {"provider": source, "source": str(data.get("source") or source),
            "provider_id": str(data.get("external_id") or data.get("fixture_id") or ""),
            "values": values, "groups": clocks, "raw": raw}


def _freshness(evidence, group, now):
    meta = dict(evidence.get("groups", {}).get(group) or {})
    dt = instant(meta.get("observed_at"))
    age = (now - dt).total_seconds() if dt else None
    state = str(meta.get("state") or "AVAILABLE").upper()
    ttl = TTL[group]
    status = str(meta.get("match_status_at_receipt") or evidence.get("values", {}).get("status") or "").upper()
    # Settled match evidence ages slowly, but odds never inherit that exception.
    if group in {"state", "stats", "events"} and status in {"FT", "AET", "PEN", "FINALIZADO", "FINISHED", "MATCH FINISHED"}:
        ttl = 30 * 86400
    elif group == "state" and status in {"NS", "SCHEDULED", "NOT STARTED", "UPCOMING", "PROGRAMADO"}:
        ttl = 86400
    reason = (state if state in UNAVAILABLE else "EXPLICIT_STALE_EVIDENCE" if state == "STALE" else "MISSING_OBSERVED_AT" if age is None else
              "FUTURE_OBSERVATION" if age < -60 else "TTL_EXPIRED" if age > ttl else "")
    if group == "odds" and not reason and instant(meta.get("fetched_at")) is None:
        reason = "MISSING_FETCHED_AT"
    return {**meta, "age_seconds": age, "ttl_seconds": ttl, "stale": bool(reason), "stale_reason": reason,
            "availability": state, "fetched_at": meta.get("fetched_at"), "observed_at": meta.get("observed_at")}


def resolve_match(match_id, evidence, *, now=None):
    """Bounded reusable materialization; every caller owns its returned graph."""
    evaluated = instant(now) or datetime.now(timezone.utc)
    evidence = list(evidence)
    digest = hashlib.sha256(json.dumps(evidence, sort_keys=True, default=str).encode()).hexdigest()
    key = (str(match_id), digest)
    with _CACHE_LOCK:
        cached = _RESOLVED_CACHE.get(key)
        if cached and instant(cached["evaluated_at"]) <= evaluated < instant(cached["valid_until"]):
            _RESOLVED_CACHE.move_to_end(key)
            return clone_snapshot(cached)
    result = _resolve_match(match_id, evidence, now=evaluated)
    with _CACHE_LOCK:
        _RESOLVED_CACHE[key] = result
        _RESOLVED_CACHE.move_to_end(key)
        while len(_RESOLVED_CACHE) > 256:
            _RESOLVED_CACHE.popitem(last=False)
    return clone_snapshot(result)


def _resolve_match(match_id, evidence, *, now=None):
    """Deterministic field winners with reasons and rejected alternatives."""
    now = instant(now) or datetime.now(timezone.utc)
    receipts = clone_snapshot(list(evidence))
    fingerprints = {id(r): hashlib.sha256(json.dumps(r, sort_keys=True, default=str).encode()).hexdigest() for r in receipts}
    freshness = {(id(r), group): _freshness(r, group, now) for r in receipts for group in GROUPS}
    decisions = {}
    for group, fields in GROUPS.items():
        for field in fields:
            choices = []
            for receipt in receipts:
                value = receipt.get("values", {}).get(field)
                fresh = freshness[id(receipt), group]
                absence = fresh["availability"] in ABSENCE
                if not _present(value) and not absence:
                    continue
                provider = provider_name(fresh.get("provider") or receipt.get("provider"))
                order = PRECEDENCE[field]
                rank = order.index(provider) if provider in order else len(order)
                dt = instant(fresh.get("observed_at"))
                receipt_id = fingerprints[id(receipt)]
                key = (bool(fresh["stale"]), absence, rank, -(dt.timestamp() if dt else 0), receipt_id)
                choices.append((key, value, receipt, fresh, provider))
            choices.sort(key=lambda c: c[0])
            usable = [c for c in choices if c[3]["availability"] not in UNAVAILABLE]
            winner = usable[0] if usable else None
            alternatives = [{"provider": c[4], "value": c[1], "observed_at": c[3].get("observed_at"),
                             "stale_reason": c[3]["stale_reason"], "availability": c[3]["availability"]} for c in choices]
            decisions[field] = {
                "value": clone_snapshot(winner[1]) if winner else None,
                "receipt_id": winner[0][4] if winner else None,
                "provider": winner[4] if winner else None,
                "source": winner[3].get("source") or winner[2].get("source") if winner else None,
                "observed_at": winner[3].get("observed_at") if winner else None,
                "fetched_at": winner[3].get("fetched_at") if winner else None,
                "stale_reason": winner[3]["stale_reason"] if winner else "NO_USABLE_EVIDENCE",
                "ttl_seconds": winner[3]["ttl_seconds"] if winner else TTL[group],
                "availability": winner[3]["availability"] if winner else "UNAVAILABLE",
                "reason": "FRESH_THEN_REAL_DATA_THEN_FIELD_PRECEDENCE_THEN_LATEST_THEN_HASH" if winner else "NO_USABLE_EVIDENCE",
                "alternatives": alternatives,
                "conflict": len({json.dumps(c[1], sort_keys=True, default=str) for c in choices}) > 1,
            }
    values = {key: d["value"] for key, d in decisions.items()}
    # State, score pair and minute describe one observation. Field policies above
    # are deliberately identical for that coherence group; never stitch goals.
    state = decisions["status"]
    state_receipts = [r for r in receipts if fingerprints[id(r)] == state["receipt_id"]]
    anchor = state_receipts[0] if state_receipts else None
    for field in ("home_score", "away_score", "minute"):
        val = anchor.get("values", {}).get(field) if anchor else None
        decisions[field] = {**clone_snapshot(state), "value": val, "reason": "STATE_COHERENCE_ANCHOR",
                            "alternatives": decisions[field]["alternatives"], "conflict": decisions[field]["conflict"]}
        values[field] = val
    values["score"] = (f"{values['home_score']}-{values['away_score']}"
                       if values["home_score"] is not None and values["away_score"] is not None else None)
    decisions["score"] = {**clone_snapshot(state), "value": values["score"], "reason": "COHERENT_SCORE_PAIR"}
    truth_input = {"id": str(match_id), **values, "last_synced_at": state["observed_at"]}
    if anchor:
        truth_input.update(anchor["values"].get("_status_signals") or {})
    truth = match_status_truth(truth_input, now=now)
    phases = {"UPCOMING": "scheduled", "LIVE": "live", "HALFTIME": "halftime", "FINISHED": "finished",
              "ARCHIVED": "finished", "POSTPONED": "postponed", "CANCELLED": "cancelled",
              "SUSPENDED": "suspended", "ABANDONED": "suspended", "STALE": "stale"}
    phase = phases.get(truth["lifecycle"], "unknown")
    if (state["stale_reason"] and phase in {"live", "halftime"}) or (state["stale_reason"] in {"TTL_EXPIRED", "FUTURE_OBSERVATION"} and phase == "scheduled"):
        phase = "stale"
        truth.update(lifecycle="STALE", is_live=False, is_stale=True, stale_reason=state["stale_reason"])
    if phase not in {"live", "halftime"}:
        values["minute"] = None
        decisions["minute"]["value"] = None
    kickoff = instant(values.get("kickoff_iso"))
    madrid = kickoff.astimezone(MADRID) if kickoff else None
    odds = decisions["odds_h2h_json"]
    odds_value = _json(odds["value"])
    def valid_price(value):
        try:
            return type(value) is not bool and math.isfinite(float(value)) and float(value) > 1
        except (ValueError, TypeError):
            return False
    outcomes = odds_value.get("outcomes") if isinstance(odds_value, dict) else []
    outcomes = outcomes if isinstance(outcomes, list) else []
    valid_market = any(isinstance(o, dict) and o.get("name") and valid_price(o.get("price")) for o in outcomes)
    odds_usable = bool(valid_market and odds["provider"] == "the_odds_api" and odds["observed_at"]
                       and odds["fetched_at"] and not odds["stale_reason"])
    deadlines = [now + timedelta(seconds=60)]
    if kickoff and kickoff > now:
        deadlines.append(kickoff)
    for receipt in receipts:
        for group in GROUPS:
            fresh = freshness[id(receipt), group]
            dt = instant(fresh.get("observed_at"))
            if dt and not fresh["stale"]:
                deadlines.append(dt + timedelta(seconds=fresh["ttl_seconds"]))
            elif dt and fresh["stale_reason"] == "FUTURE_OBSERVATION":
                deadlines.append(dt - timedelta(seconds=60))
    # Existing normalized team/competition/player contracts remain the public
    # entity language. IDs retain provider namespaces, never name-only merging.
    from engines.sports_domain_model_engine import normalize_team_entity, normalize_competition_entity, normalize_player_entity
    identity_row = dict(values)
    def mapped_entity(field):
        reference = decisions[field]["receipt_id"]
        return next((r.get("entity_mappings", {}).get(field) for r in receipts if fingerprints[id(r)] == reference), None)
    teams = {side: normalize_team_entity({**identity_row, "canonical_team_id": mapped_entity(f"{side}_team_id")}, side=side, provider=decisions[f"{side}_team_id"]["provider"] or decisions[f"{side}_team"]["provider"])
             for side in ("home", "away")}
    competition = normalize_competition_entity({**identity_row, "canonical_competition_id": mapped_entity("competition_id")}, provider=decisions["competition_id"]["provider"] or decisions["competition_name"]["provider"])
    players = values.get("players") or []
    player_mappings = next((r.get("player_mappings", {}) for r in receipts if fingerprints[id(r)] == decisions["players"]["receipt_id"]), {})
    players = [normalize_player_entity({**p, "canonical_player_id": p.get("canonical_player_id") or player_mappings.get(str(p.get("id") or p.get("player_id")))}, provider=decisions["players"]["provider"]) for p in players if isinstance(p, dict)] if isinstance(players, list) else []
    return {"contract": CONTRACT, "canonical_match_id": str(match_id), "phase": phase,
            "teams": teams, "competition": competition, "players": players,
            "valid_until": min(deadlines).isoformat(),
            "resolved": decisions, "values": values, "status_truth": truth,
            "kickoff_madrid": madrid.isoformat() if madrid else None,
            "timezone": "Europe/Madrid", "evaluated_at": now.isoformat(),
            "odds_snapshot": {"canonical_id": f"odds:{match_id}:{odds['observed_at']}",
                              "markets": odds_value, "usable": odds_usable,
                              "provider_timestamp": odds["observed_at"], "provenance": clone_snapshot(odds)},
            "provider_evidence": receipts}


def legacy_projection(row, canonical):
    """Preserve route/DB identifiers and unrelated business/media fields."""
    result = dict(row)
    result.update({k: v for k, v in canonical["values"].items() if not k.startswith("_")})
    result["score"] = canonical["values"].get("score") or ""  # Legacy string contract; canonical unknown stays None.
    truth = canonical["status_truth"]
    result["status"] = (canonical["resolved"]["status"]["value"] if not truth["status_conflict"] and truth["lifecycle"] in {"LIVE", "HALFTIME", "FINISHED", "ARCHIVED"} else
                        {"UPCOMING": "NS", "FINISHED": "FT", "HALFTIME": "HT", "RESULT_PENDING": "TBD", "INCOMPLETE": "TBD"}.get(truth["lifecycle"], truth["lifecycle"]))
    result["_observed_status"] = canonical["resolved"]["status"]["value"]
    result["last_synced_at"] = canonical["resolved"]["status"]["observed_at"]
    result["source"] = canonical["resolved"]["status"]["source"] or result.get("source")
    result["unified_sports_truth"] = canonical
    if canonical["kickoff_madrid"]:
        dt = instant(canonical["kickoff_madrid"]).astimezone(MADRID)
        result.update(kickoff_iso=dt.isoformat(), match_date=dt.date().isoformat(), kickoff_time=dt.strftime("%H:%M"), match_time=dt.strftime("%H:%M"))
    if not canonical["odds_snapshot"]["usable"]:
        result["odds_h2h_json"] = None
    return result












def adapt_section(group, payload, context):
    """Provider arrays -> existing consumer shapes, preserving absent values."""
    if not isinstance(payload, list):
        return payload
    if group == "events":
        return [{"provider_event_id": event.get("id"), "event_type": event.get("type"),
                 "detail": event.get("detail"), "minute": (event.get("time") or {}).get("elapsed"),
                 "added_time": (event.get("time") or {}).get("extra"),
                 "team_id": (event.get("team") or {}).get("id"), "team_name": (event.get("team") or {}).get("name"),
                 "player_id": (event.get("player") or {}).get("id"), "player_name": (event.get("player") or {}).get("name"),
                 "source": "api_football"} if isinstance(event.get("time"), dict) else clone_snapshot(event)
                for event in payload if isinstance(event, dict)]
    if group == "stats":
        cards = {}
        for block in payload:
            if not isinstance(block, dict):
                continue
            team = block.get("team") or {}
            side = next((s for s in ("home", "away") if
                         (_present(context.get(f"{s}_team_id")) and str(team.get("id")) == str(context[f"{s}_team_id"]))
                         or (context.get(f"{s}_team") and team.get("name") == context[f"{s}_team"])), None)
            if not side:
                continue
            for stat in block.get("statistics") or []:
                if not stat.get("type") or stat.get("value") is None:
                    continue
                label = str(stat["type"])
                card = cards.setdefault(label, {"key": label.lower().replace(" ", "_"), "label": label, "home": None, "away": None, "leader": "even"})
                card[side] = str(stat["value"])
        return {"available": bool(cards), "items": list(cards.values()), "source": "api_football", "external_calls": 0}
    if group == "lineups" and any(isinstance(b, dict) and "startXI" in b for b in payload):
        rows = []
        for block in payload:
            team = block.get("team") or {}
            for key, starting in (("startXI", True), ("substitutes", False)):
                for item in block.get(key) or []:
                    p = item.get("player") or {}
                    rows.append({"team_id": team.get("id"), "team_name": team.get("name"),
                                 "player_id": p.get("id"), "player_name": p.get("name"),
                                 "number": p.get("number"), "position": p.get("pos"), "grid": p.get("grid"),
                                 "formation": block.get("formation"), "is_starting": starting, "source": "api_football"})
        return rows
    return payload


def canonicalize_detail(detail, *, now=None):
    """Fold existing local depth adapters into the same audited match contract.

    Caller already acquired these rows. No queries or provider calls here.
    Presentation wrappers stay intact; clocks come from actual persisted rows.
    """
    match = detail.get("match") or {}
    canonical = match.get("unified_sports_truth") or resolve_match(match.get("id") or "", [evidence_from_row(match)], now=now)
    receipts = list(canonical["provider_evidence"])
    tracker = detail.get("api_football_live_tracker") or {}
    # Older databases have live depth rows but no Phase 3 receipt yet. Their
    # actual captured_at clocks remain usable; the fixture clock is not a
    # substitute for the statistics/events capture clock.
    tracker_stats = tracker.get("stats") or {}
    raw_stats = [r for team in tracker_stats.get("teams", []) if isinstance(team, dict) for r in team.get("raw", []) if isinstance(r, dict)]
    stat_cards = [{k: v for k, v in card.items() if k not in {"home_numeric", "away_numeric"}}
                  for card in tracker.get("stat_cards") or [] if isinstance(card, dict)]
    for group, rows, value in (
        ("stats", raw_stats, {"available": bool(stat_cards), "items": stat_cards, "source": tracker.get("provider")}),
        ("events", tracker.get("events") or [], tracker.get("events") or []),
    ):
        if not rows:
            continue
        clocks = [instant(r.get("captured_at")) for r in rows if isinstance(r, dict)]
        stamp = min(clocks).isoformat() if clocks and all(clocks) else None
        receipt = evidence_from_row({"source": tracker.get("provider") or "api_football", group: value,
            "last_synced_at": stamp, "raw_json": json.dumps({group: rows}, default=str)})
        terminal_observed = instant(canonical.get("resolved", {}).get("status", {}).get("observed_at"))
        if terminal_observed and instant(stamp) and instant(stamp) >= terminal_observed:
            receipt["groups"][group]["match_status_at_receipt"] = match.get("status")
        receipts.append(receipt)
    for group, key in (("lineups", "lineups"), ("stats", "cached_statistics"), ("video", "media"), ("h2h", "head_to_head"), ("standings", "standings")):
        value = detail.get(key)
        if not value or (isinstance(value, dict) and value.get("available") is False):
            continue
        rows = value.get("items", []) if isinstance(value, dict) else value
        rows = rows if isinstance(rows, list) else []
        stamps = [r.get("captured_at") or r.get("observed_at") or r.get("last_synced_at") for r in rows if isinstance(r, dict)]
        valid = [instant(s) for s in stamps if instant(s)]
        stamp = value.get("captured_at") if isinstance(value, dict) else None
        if isinstance(value, dict) and value.get("source") == "api_football_stats_cache":
            stamp = stamp or value.get("updated_at")  # Adapter explicitly exports captured_at here.
        stamp = stamp or (max(valid).isoformat() if valid else None)
        provider = value.get("source") if isinstance(value, dict) else next((r.get("source") for r in rows if isinstance(r, dict) and r.get("source")), None)
        if not provider and group in {"lineups", "stats"}:
            provider = "api_football"
        receipt = evidence_from_row({"source": provider or "local_cache", group: value, "last_synced_at": stamp})
        terminal_observed = instant(canonical.get("resolved", {}).get("status", {}).get("observed_at"))
        captured = instant(stamp)
        if terminal_observed and captured and captured >= terminal_observed:
            receipt["groups"][group]["match_status_at_receipt"] = match.get("status")
        receipts.append(receipt)
    unified = resolve_match(canonical["canonical_match_id"], receipts, now=now)
    detail["match"] = legacy_projection(match, unified)
    detail["unified_sports_truth"] = unified
    # Depth consumers can audit the selected groups without introducing UI.
    # Media retains the existing rights/access policy. Provider evidence must
    # never promote an unreviewed URL into a licensed highlight component.
    for group, key in (("lineups", "lineups"), ("stats", "cached_statistics"), ("h2h", "head_to_head"), ("standings", "standings")):
        selected = unified["values"].get(group)
        if selected is not None:
            detail[key] = selected
    if unified["values"].get("events") is not None:
        detail["timeline"] = unified["values"]["events"]
    return detail


def refresh_payload_truth(payload, *, now=None):
    """Renew cached field decisions at their deadlines without database reads."""
    evaluated = instant(now) or datetime.now(timezone.utc)
    refreshed = {}
    def visit(value):
        if isinstance(value, list):
            return [visit(item) for item in value]
        if not isinstance(value, dict):
            return value
        canonical = value.get("unified_sports_truth")
        if isinstance(canonical, dict) and canonical.get("contract") == CONTRACT:
            if instant(canonical["evaluated_at"]) <= evaluated < instant(canonical["valid_until"]):
                return value
            if isinstance(value.get("match"), dict):
                # A detail envelope is not a match row. Renew its nested match
                # and selected sections together, retaining media policy.
                result = {**value, "match": visit(value["match"])}
                renewed = result["match"].get("unified_sports_truth") or canonical
                result["unified_sports_truth"] = renewed
                for group, key in (("stats", "cached_statistics"), ("lineups", "lineups"),
                                   ("events", "timeline"), ("h2h", "head_to_head"), ("standings", "standings")):
                    if renewed["values"].get(group) is not None:
                        result[key] = renewed["values"][group]
                return result
            # Same snapshot may appear in several lanes. Resolve it once.
            evidence_hash = hashlib.sha256(json.dumps(canonical["provider_evidence"], sort_keys=True, default=str).encode()).hexdigest()
            key = (canonical["canonical_match_id"], canonical["evaluated_at"], evidence_hash)
            if key not in refreshed:
                refreshed[key] = resolve_match(key[0], canonical["provider_evidence"], now=evaluated)
            return legacy_projection(value, refreshed[key])
        return {key: visit(item) for key, item in value.items()}
    return visit(payload)

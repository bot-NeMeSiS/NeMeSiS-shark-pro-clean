"""Request-local selection over an existing sports snapshot; no IO or shared state."""
from copy import deepcopy


def build_personal_agenda(summary, favorites, *, normalize, status_for, kickoff_for, now):
    if favorites is None:
        return {"state": "UNAVAILABLE", "saved_count": None, "matches": []}
    saved = {kind: set() for kind in ("team", "league", "match")}
    for row in favorites:
        if row.get("kind") in saved and row.get("value"):
            saved[row["kind"]].add(normalize(row["value"]))
    count = sum(map(len, saved.values()))
    if not count:
        return {"state": "EMPTY", "saved_count": 0, "matches": []}
    if summary.get("storage_status") != "ok":
        return {"state": "UNAVAILABLE", "saved_count": count, "matches": []}
    seen, selected = set(), []
    # These are existing bounded sports-truth lists, never another query/feed.
    for key in ("all_valid_matches", "valid_matches_today", "valid_upcoming_matches", "valid_live_events", "finished_matches"):
        for match in summary.get(key) or []:
            match_id = str(match.get("id") or "")
            if not match_id or match_id in seen:
                continue
            seen.add(match_id)
            reasons = []
            if normalize(match_id) in saved["match"]:
                reasons.append("Partido guardado")
            if any(normalize(match.get(field) or "") in saved["team"] for field in
                   ("home_team", "away_team", "safe_home", "safe_away", "client_home", "client_away")):
                reasons.append("Sigues a un equipo")
            if any(normalize(match.get(field) or "") in saved["league"] for field in
                   ("competition_key", "competition_name", "league_name", "calendar_competition")):
                reasons.append("Sigues esta competición")
            if not reasons:
                continue
            status = status_for(match)
            kickoff = kickoff_for(match)
            # A saved stale fixture is not a forthcoming game or a confirmed result.
            if status.get("is_live"):
                rank, order = 0, kickoff.timestamp() if kickoff else 0
            elif status.get("is_upcoming") and kickoff and kickoff >= now:
                rank, order = 1, kickoff.timestamp()
            elif status.get("is_finished") and kickoff and kickoff <= now:
                rank, order = 2, -kickoff.timestamp()
            else:
                continue
            item = deepcopy(match)
            item["is_favorite"] = True
            item["personal_reason"] = reasons[0]
            selected.append((rank, order, match_id, item))
    selected.sort(key=lambda row: row[:3])
    return {"state": "READY" if selected else "NO_MATCHES", "saved_count": count,
            "matches": [row[3] for row in selected[:3]]}

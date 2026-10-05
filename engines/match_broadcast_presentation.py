"""Present the existing persisted TV contract without provider or database I/O."""
from datetime import datetime, timedelta, timezone


def broadcast_presentation(history, *, now=None):
    current = now or datetime.now(timezone.utc)
    rows = ((history or {}).get('details') or {}).get('broadcasts') or []
    snapshots = []
    for row in rows:
        payload = row.get('payload') or {}
        try:
            observed = datetime.fromisoformat(str(payload.get('observed_at') or '').replace('Z', '+00:00'))
            if observed.tzinfo is None or observed > current:
                continue
        except (ValueError, TypeError):
            continue
        snapshots.append((observed, payload))
    empty = dict(available=False, channels=[], updated_at=None, stale=False)
    if not snapshots:
        return empty
    observed, payload = max(snapshots, key=lambda item: item[0])
    if current - observed > timedelta(hours=12):
        return dict(empty, stale=True, updated_at=observed.isoformat())
    channels = []
    seen = set()
    for row in payload.get('channels') or []:
        if not isinstance(row, dict):
            continue
        name = str(row.get('channel') or '').strip()[:160]
        country = str(row.get('country') or '').strip()[:120]
        identity = (name.casefold(), country.casefold())
        if not name or identity in seen:
            continue
        seen.add(identity)
        channels.append(dict(channel=name, country=country))
    channels.sort(key=lambda row: (row['country'].casefold() not in {'spain', 'españa'}, row['country'], row['channel']))
    return dict(available=bool(channels) and payload.get('available') is True,
                channels=channels[:8] if payload.get('available') is True else [],
                updated_at=observed.isoformat(), stale=False)

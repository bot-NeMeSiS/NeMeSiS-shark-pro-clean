# Sports Core Provider Adapters Audit

## Current Provider Shapes Found

API-Football live tracker stores fixtures, events and statistics using provider-specific rows in `api_football_live_snapshots`, `api_football_live_events` and `api_football_live_stats`.

Legacy matches use fields such as id, external_id, competition_name, league_name, home_team, away_team, status, minute, score, home_score, away_score, raw_json and updated_at.

Live Story previously normalized event display independently. It now preserves that output while attaching Timeline Event Entity.

Match Intelligence previously consumed match/timeline/tracker dictionaries directly. It now accepts canonical match and timeline inputs without dropping the existing API.

Telegram Intelligence previously consumed Match Intelligence and sports metrics. It now also exposes a Sports Core read-only envelope when domain data is available.

## Consolidation Applied

- New adapter functions normalize provider/cache rows into canonical entities.
- Provider IDs are namespaced, for example `api_football:match:4242`.
- UI and SHARK retain compatibility while the canonical entity becomes the internal shared language.
- No external provider calls were added.

## Still Legacy

- Provider sync jobs still write their existing normalized cache tables during scheduled syncs.
- Some screens still read legacy match dictionaries for display.
- Full Team/Competition/Player Centers are not implemented yet.

## Safe Migration Path

1. Keep legacy display fields while adding canonical entities.
2. Move future Sports Core modules to canonical entities first.
3. Migrate existing consumers one by one.
4. Remove legacy helpers only after consumer scans prove no use.

# V934 Realtime Matches And Live QA

## Engine policy

- Source order: normalized local DB/cache context, then safe stale cache, then honest empty state.
- No external provider call is permitted during page render or API polling.
- Live poll recommendation: 45 seconds when confirmed live events exist.
- Idle poll recommendation: 180 seconds when no event is live.
- In-process snapshot TTL: 15 seconds.
- Live data becomes stale after 120 seconds.
- Hidden browser tabs pause polling; failures use exponential backoff within safe limits.

## Validated transitions

- scheduled -> live
- live score/minute update
- halftime
- finished
- incomplete match rejection
- stale cache fallback

The executed worker reported `waiting_for_real_data`, with zero external calls and zero database writes. This is a valid safe state, not an error and not sample data.

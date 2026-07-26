# Sports Core Freshness And Stale Policy

## States

- fresh: inside the fresh tolerance for the data type and match state.
- aging: outside fresh tolerance but still usable with caution.
- stale: outside stale tolerance and not usable for live intelligence.
- unknown: timestamp missing or unparsable.
- unavailable: data not present.

## Live Tolerance

Live states use tighter tolerances. A live match snapshot can only support live intelligence while it is fresh or aging. Stale live data must not become pressure, dominance, rhythm or apparent live status.

## Scheduled/Finished Tolerance

Scheduled and finished matches tolerate longer cache windows because they are less volatile, but missing or stale data must still be visible as a limitation.

## Match Intelligence Rule

MATCH-INTELLIGENCE-EVIDENCE-V1 keeps stale evidence explicit. Stale inputs cannot create provider pressure, dominance or rhythm.

## Telegram Rule

Telegram receives freshness in a read-only envelope. The contract does not authorize sends and does not convert stale sports data into publishable content.

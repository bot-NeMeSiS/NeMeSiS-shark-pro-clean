# The Odds API: credentials and conservative consumption

The existing `THE_ODDS_API_KEY` continues to work. No Render secret needs to be
changed for the current FREE account. Optional credentials are selected in order:
`THE_ODDS_API_KEY_PAID`, `THE_ODDS_API_KEY_FREE`, then `THE_ODDS_API_KEY` (LEGACY).
Values are never compared or retained in diagnostics: no prefixes, hashes or
secret-derived identifiers. The tier describes the configured slot, not a verified
subscription plan. No provider subscription is changed.

A real GET request uses the primary credential. Only HTTP 401/403 together with
`INVALID_KEY`, `DEACTIVATED_KEY` or `UNAUTHORIZED` permits **one** retry with the
next configured slot. If that slot also fails, the refresh stops. No fallback for
quota exhaustion, 429, rate limits, timeout, network errors, 5xx or unknown errors.
The selected slot is retained only within that refresh, so the next real refresh
tries PAID again. There is no new auth probe or preflight request.

FREE and, by default, LEGACY use an internal profile:

| Variable | Default | Meaning |
| --- | --- | --- |
| `ODDS_FREE_MAX_COMPETITIONS` | `1` | Maximum competitions per refresh |
| `ODDS_FREE_REFRESH_MINUTES` | `360` | Minimum interval between FREE attempts |
| `ODDS_FREE_MAX_REGIONS` | `1` | First configured regions used internally |
| `ODDS_FREE_MAX_MARKETS` | `1` | Configured markets, prioritizing h2h when present |
| `ODDS_LEGACY_PROFILE` | `FREE` | Use `PAID` only for a known paid legacy account |

All limits accept positive integers; malformed values use the defaults. The normal
`ODDS_CACHE_MINUTES` still applies and can make the interval longer. The profile
does not modify `ODDS_REGIONS` or `ODDS_MARKETS`, invent markets, delete snapshots,
or replace cached coverage. A smaller refresh updates only observed events.
Selection does not rotate competitions or promise full coverage under FREE.
Increasing limits increases consumption; multiple keys never extend a quota.

PAID can recover at the next normal refresh even if FREE's interval has not
expired. If PAID is rejected while FREE's interval is still active, the refresh
defers FREE with `FREE_BUDGET`; a safe timestamp of the last FREE attempt survives
that deferral. Existing Cron deadlines remain in force before either attempt.

Diagnostics include `credential_tier_selected`, `fallback_used`, provider HTTP,
allowlisted provider error code and numeric quota headers. `external_calls` counts
both attempts. `CACHE_REUSED` is historical evidence and does not certify current
authentication. Verify a natural tick with a current provider observation after
deployment, without manually calling Odds or Telegram. Sports/Odds/Telegram
remain separate; #187 remains DRAFT and Phase 4 remains blocked.

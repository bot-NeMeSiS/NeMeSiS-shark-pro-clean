# The Odds API: credentials, application coverage, and conservative consumption

This document describes the local integration; it does **not** verify that any
credential is present or valid, that the provider account is active, or which
subscription plan is contracted. Credential-slot names and configured defaults
are not evidence of a provider plan. Do not change Render secrets or increase
markets, regions, competitions, or refresh frequency without verifying the plan
and its limits first.

Optional credentials are selected in order:
`THE_ODDS_API_KEY_PAID`, `THE_ODDS_API_KEY_FREE`, then `THE_ODDS_API_KEY` (LEGACY).
Values are never compared or retained in diagnostics: no prefixes, hashes or
secret-derived identifiers. The tier describes the configured slot, not a verified
subscription plan. No provider subscription is changed.

## What the application currently uses

The scheduled odds request defaults to the `h2h` market (`ODDS_MARKETS=h2h`),
and the normalized snapshot table currently stores only the home/draw/away prices
for that market. The original event payload is retained with that snapshot, but
other market families such as totals, both-teams-to-score, or handicaps are not
currently normalized into the customer-facing combi builder. A provider plan may
offer more markets; that does not make them active in this application.

The PRO/ELITE combi builder can show a normalized 1X2 market reference from the
already stored snapshot only when all three decimal prices are valid, eligible,
from the same bookmaker and snapshot, and carry a verified provider quote time.
This is a price-derived market reference, not a SHARK forecast or a calibrated
joint probability for a combination. The page performs no provider request and
reports zero external calls. Missing, stale, receipt-only, inconsistent, or
invalid data fails closed with an explanation.

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

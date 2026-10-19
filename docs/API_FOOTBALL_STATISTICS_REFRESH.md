# API-Football: periodic match statistics

## Problem corrected

The sports cycle refreshed the fixture window and the live scoreboard with
`deep_limit=0`. Statistics were left to a multi-capability enrichment sample
limited to one fixture and a long refresh interval. That was insufficient to
populate the match pages. The client also hid the statistics section when its
cache was empty.

## Collection and storage

`run_sports_sync_cycle` now runs `refresh_api_football_statistics_if_due` after
fixture/live refresh and before the existing deep enrichment. The new stage does
not inherit the deep sample's scheduling interval. It selects due live fixtures
and completed fixtures from the preceding 48 hours, using proven API-Football
identities and rotating by the oldest collection attempt.

The default request is `GET /fixtures?ids=id1-id2-...`, with at most 20 fixture IDs
and one request per batch. API-Football documents this form as returning the
available match detail blocks, including statistics, subject to the plan's
support. Only the statistics block is persisted by this job. Returned blocks
are matched by fixture ID, independently of their response order. Unknown IDs,
duplicate fixture blocks and mismatched teams cannot populate another match.

Statistics are committed to the existing live and historical stores, with a
statistics observation time. A valid new snapshot replaces the previous live
statistics snapshot atomically. An empty response preserves the last usable
snapshot and records the missing-data outcome. A measured zero remains zero;
an absent or null metric remains unavailable. Collecting statistics does not
advance the fixture's score, minute, lifecycle or provider observation clock.

The writer reserves the existing shared API usage ledger in the same short
transaction that claims the fixtures. The transaction is committed before HTTP.
Claims, bounded SQLite waits, the Cron request deadline, negative-result caches
and provider-failure backoff prevent overlapping work and uncontrolled retries.
The ledger is a local request budget, not a measurement of the provider's
remaining quota.

## Configuration

Defaults apply without adding new deployment variables. Existing provider and
network switches still apply. Credentials use the already supported names
`API_FOOTBALL_KEY`, `API_FOOTBALL_API_KEY`, `API_SPORTS_KEY` and `APISPORTS_KEY`,
with the existing shared resolver's precedence.

| Variable | Default | Purpose |
| --- | --- | --- |
| `ENABLE_API_FOOTBALL_STATISTICS_SYNC` | `true` | Enable the dedicated writer. |
| `API_FOOTBALL_STATISTICS_TRANSPORT` | `batch` | Use batched fixtures; explicit alternative: `individual`. |
| `API_FOOTBALL_STATISTICS_BATCH_SIZE` | `20` | Maximum due fixtures per tick, clamped to 0–20. |
| `API_FOOTBALL_STATISTICS_INDIVIDUAL_LIMIT` | `2` | Requests per tick in individual mode, capped at 4. |
| `API_FOOTBALL_STATISTICS_LIVE_TTL_SECONDS` | `300` | Minimum interval after successful live statistics. |
| `API_FOOTBALL_STATISTICS_FINAL_TTL_SECONDS` | `21600` | Minimum interval after successful final statistics. |
| `API_FOOTBALL_STATISTICS_EMPTY_TTL_SECONDS` | `1800` | Delay after an empty response. |
| `API_FOOTBALL_STATISTICS_FAILURE_BACKOFF_SECONDS` | `21600` | Backoff for an observed provider restriction. |

All requests remain subject to `API_FOOTBALL_DAILY_CALL_BUDGET` (local application
guard default: 600 reserved calls/day), the Cron deadline and the actual sports
scheduler cadence. This internal safety cap is not the provider quota and does
not verify a subscription. An explicit Render value still overrides the default.
A `DAILY_BUDGET` receipt identifies the local guard, includes its limit/usage and
states that provider quota was not consulted; it must not be read as an API plan
or account-quota rejection. A TTL is a minimum reuse interval, not
a promise that a job ran at that exact frequency. A live-to-final transition
makes the final statistics eligible without waiting for the prior live TTL.

For a plan without the `ids` facility, `individual` explicitly uses
`/fixtures/statistics?fixture=...` with the same ledger, claims and rotation.
There is no automatic second transport attempt after an authentication, quota
or plan rejection. Verify the provider's response and plan before changing that
setting. This change does not modify the provider subscription or its limits.

## Display and operational evidence

The match page always exposes one Statistics section and its navigation link.
When data is missing, it explains whether collection is pending, the provider
returned no statistics, or collection is interrupted. Existing data can remain
visible with its own observation time and a pending/interrupted update message.
The page does not turn a successful scoreboard refresh into fresh statistics.

The existing `/api/matches/<match_id>/statistics` response retains the legacy
`statistics` field and adds `statistics_context`, containing the canonical
cached items, collection state and safe message. Both that GET and the match
page, including `?refresh=1`, read local evidence without provider requests or
business/database mutations.

The sports result, compact Cron receipt, runner diagnostics and provider-health
panel include a separate `statistics_refresh` stage. It reports refreshed
fixtures, persisted metrics, empty responses, failures and request count without
exposing raw provider errors or credentials. Access/coverage failures remain
visible; a skipped or cached attempt does not become a new provider observation.

## Validation and release checks

Focused automated regressions:

```sh
python -m pytest tests/test_api_football_statistics_refresh.py \
  tests/test_statistics_refresh_integration.py \
  tests/test_match_statistics_zero.py \
  tests/test_sports_pipeline_stage_truth.py -q
```

They use synthetic databases and mocked transports. They cover provider-to-SQL-
to-context-to-HTML/API delivery, rotation while deep enrichment is not due,
shared quota, concurrent claims, empty/invalid/restricted responses, identity
collisions, missing data versus zero, independent timestamps and read-only GETs.
The dedicated regressions are also included in the repository CI workflow.

After the protected-main release and existing Render auto-deploy, confirm the
new Git SHA from `/api/runtime-version`, allow an existing sports cycle to run,
and inspect both the statistics stage and actual match data. A configured API
key or a successful build alone does not prove statistics were delivered.
Provider coverage, account access and the current local budget must still allow
a collection request. No production delivery result is asserted by this file.

## Rollback

Set `ENABLE_API_FOOTBALL_STATISTICS_SYNC=false` to stop the dedicated writer
while retaining its collected data. For a code rollback, revert this focused
change through the normal protected-main workflow and let Render auto-deploy.
The new scheduling table is additive; rollback requires no destructive database
migration or removal of historical statistics.

## Provider references

- [API-Sports football documentation](https://api-sports.io/documentation/football/v3)
- [API-Football call and quota optimization](https://www.api-football.com/news/post/how-to-optimize-api-sports-calls-and-quota-usage)

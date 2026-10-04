# Postmatch lifecycle in the existing master

The existing Render master remains the only Cron. It runs sports lifecycle/result synchronization, pick grading and track record through the existing daily automation callbacks (`app.py:v818_results_sync_and_top_results`, `v818_daily_close_previous_day`). Factual recaps and history use persisted match data (`app.py:v769_highlight_match_context`, `engines.match_context_engine`). No invented results, player metrics or summaries are introduced.

## Durable recovery

The authenticated `/api/automation/postmatch/tick` continues through `engines.postmatch_recovery.tick`. Production adds an `archive` job alongside existing statistics and highlight tracking. Two jobs and a 20-second deadline remain the per-tick bounds. Approved source settings stay unchanged; no source is activated by deployment.

Discovery keeps the recent seven-day lane and adds a persistent, 250-row inventory cursor over canonical matches. Final status, identity and competition are required. Existing jobs retain their states across cursor cycles, restarts and deployment. Identity changes cancel unfinished old jobs; changed final periods recheck archived sections without showing incompatible receipts. Recent work precedes deep history; statistics precede archive acquisition, and reviewed editorial competition weights break ties on the same match date. Expired leases recover first.

The same source allowlist, credential, fenced lease and **60 calls per Madrid day across providers** apply to all postmatch network requests. Exact final SportsDB raw/profile evidence avoids repeat identity lookups. A durable response cache keeps up to 32 entries of at most 128 KiB, valid for six hours and bound to canonical identity plus provider/credential/request. Successful response receipts retain their original observation times after a restart. Errors, invalid top-level response shapes and credentials are not cached as successful content.

Normal production highlight jobs hand off to the existing media queue, which has its own unchanged **12 calls per six hours** ceiling. They do not buy duplicate video lookups from the critical postmatch allowance. Concrete catalogue links still pass strict reconciliation and the unchanged rights engine. Existing custom source adapters retain the two-worker interface for compatibility and isolated tests.

## Events and lineups

API-Football fixtures establish exact identity and final period before `fixtures/events` and `fixtures/lineups`; SportsDB uses its verified final event before `lookuptimeline.php` and `lookuplineup.php`. Only currently selected sources are used. Provider/event/team evidence is required; no loose matching, guessed players or generated metrics. Empty successful sections record absence at that check and schedule retries. They never imply permanent absence or full sporting coverage.

Normalized receipts bind match identity, source, reference, period and observation time. Identical receipts are idempotent. Match Center fills missing timeline/lineup sections from this evidence; existing primary sections remain authoritative and are not combined with incompatible periods. Rights approval is independent.

The postmatch archive is bounded to 16 MiB of normalized payloads and retains the **existing 128 MiB free-disk reserve**. If either storage guard blocks acquisition, `ARCHIVE_BUDGET` remains scheduled without purchasing calls. The Command Center reports the guard and stored receipts explicitly; receipt counts are not catalogue match coverage. No disk plan or production database is changed manually.

## Run truth and pending work

PASS means a technically valid check, including legitimate NO_VIDEO, NO_STATISTICS or empty event/lineup responses. Scheduled future work remains visible independently of PASS or IDLE.

PARTIAL means real deferral: day/tick budget, source cooldown, missing identity/dependency, unfinished recovery or archive capacity. These do not consume the error-attempt ceiling. Negative checks have a separate count and age-aware retry scheduling. Pending jobs survive budget exhaustion and restart.

FAIL means a real HTTP/authentication, malformed response, storage/corruption or execution error. A later empty response or cooldown cannot mask an earlier technical error. Valid fallback evidence can still be saved, with the technical failure reported separately. The five-attempt ceiling continues to surface persistent technical failures as explicit exceptions; jobs are never silently deleted.

## Provider references and validation scope

- [TheSportsDB official endpoint documentation](https://www.thesportsdb.com/documentation).
- [API-Football official integration guide](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide).

Offline tests and local HTTP Browser QA use isolated databases and blocked external requests. They certify dispatch, identity, durability, cache, budgets, output and UI behavior. They do not certify current provider entitlement, third-party playback, full catalogue coverage or production throughput. Live certification must report actual queued work, archive guards, provider restrictions and budgets after auto-deployment.

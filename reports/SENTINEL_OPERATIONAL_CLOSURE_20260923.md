# Sentinel Operational Closure · 23/09/2026

## Decision

OPS-001 is closed as **PASS_LOCAL_SAFE**. This is a verified internal-control closure,
not a claim that the durable Sentinel job executor runs in production.

## Baseline

- GitHub main at reconciliation: `228369d42447f37f3023a7f09216205057e4655c`.
- Render Web and Cron observed LIVE at that SHA.
- Exact PR #82 head `d445c380aa24482e4b30e0d5c7375444a838435c`
  passed QA, Preflight and full Smoke before merge.

## Operational contract verified

`engines/sentinel_jobs.py` provides a closed request registry for one fixed
`product_surface_review` action. It validates payload shape, scopes jobs by owner,
deduplicates identical source revisions, uses SQLite transactional claims, fences
expired leases, treats interruptions/failures as terminal, checks source revision
before and after work, and sanitizes child-process failures.

`tools/local_desktop/run_sentinel_local.py` is the supervised executor. It binds to
127.0.0.1, forces OFFLINE/LOCAL SAFE settings, disables background/pick/Telegram
automation, uses a local database under `data/local_dev`, installs the existing
process/network boundary, and runs only the fixed static/no-write/dry-run worker.

The Flask boundary requires:
- identified ADMIN session;
- LOCAL SAFE mode;
- `SENTINEL_JOBS_ENABLED`;
- job database contained under `data/local_dev`;
- live executor heartbeat;
- CSRF for submission.

Outside that boundary the durable executor returns unavailable instead of silently
queueing work. Production enablement is intentionally not part of this closure.

## CI evidence

Every `NeMeSiS Smoke Checks` run executes these isolated files in fresh processes:

1. `tests/test_project_control_http.py`
2. `tests/test_sentinel_jobs_http.py`
3. `tests/test_sentinel_operational_browser.py`

The contracts cover:
- no visitor/FREE/PRO/ELITE access;
- admin identity and per-owner isolation;
- CSRF rejection;
- closed action/parameter registry;
- GETs do not submit jobs;
- disconnected executor returns 503;
- double click plus concurrent requests create one job;
- QUEUED -> RUNNING -> COMPLETED lifecycle;
- revision fencing;
- reload/second-tab recovery;
- failure injection produces sanitized FAILED state and no retry;
- desktop/mobile viewport overflow and focus behavior;
- project-control reads do not become execution authority.

The PR #82 exact-head Smoke completed SUCCESS with these boundary tests included.

## Classification

| Layer | State |
|---|---|
| LOCAL logic/storage | PASS |
| LOCAL Flask/SQLite/browser | PASS |
| CI fresh-process Sentinel boundary | PASS |
| MAIN code | INCLUDED |
| Render application | LIVE, but durable executor disabled |
| Production Sentinel executor | NOT_ENABLED_BY_DESIGN |
| Historical 12 LOCAL_SAFE_BLOCKED | NOT_RECERTIFIED |
| Historical environmental blockers | NOT_RECERTIFIED |

## Non-claims

This closure does not:
- install a production Sentinel scheduler;
- enable a mutable production worker;
- auto-run Codex;
- push/deploy from Sentinel;
- send Telegram;
- call paid sports providers;
- mutate payments, users or memberships;
- close Directos, Design, media rights or the accumulated 19 Sep candidate.

## Continuity

The next internal block is OPS-002 Hygiene / remote reconciliation. Preserve unknown
worktree evidence and extract unique useful work before closing superseded PRs.
PR #75 still contains a shareable `/instalar` guide not yet absorbed into main;
PR #77 Telegram Ultra Pro remains DRAFT/NOT_DEPLOYED and requires separate release
review rather than automatic continuation.

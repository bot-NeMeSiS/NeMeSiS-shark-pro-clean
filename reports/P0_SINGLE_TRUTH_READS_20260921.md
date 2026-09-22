# P0: less repeated lifecycle work, without caching LIVE decisions

Baseline: PR62, `2e7bcbedbd28d0be2761ae297ca211f4e8b915e6`.
Candidate status at authoring: NOT DEPLOYED. Related issue: #61 remains open.

## Scope

Three engine changes, one regression file and this report. No app.py, database/schema,
providers, quotas, TTLs, CSS, worker/thread settings, workflows, secrets, payments,
users, permissions or Telegram delivery changes. PR59/PR60 remain independent.

The snapshot formerly evaluated the same match truth inside its realtime state and
again for its status label. `build_realtime_match_evidence` now returns those two
fresh dictionaries from one authoritative evaluation. The public
`build_realtime_match_state` API and its returned fields stay unchanged. No supplied
or persisted `status_truth` is trusted and no alternative lifecycle rules are added.

The bounded status-string transformation uses an LRU of 256 entries. Arbitrary
objects are converted and trimmed to 180 characters BEFORE admission. Only text is
retained, never fixtures, mutable graphs, timestamps, session data or LIVE decisions.
Each invocation still evaluates freshness, terminal conflicts and provider clocks.
PR62 isolation, single-flight and invalidation-generation protections stay intact.

## Local validation

- 48 new parametrized tests pass. Selection across existing logic/HTTP regressions:
  354 PASS, eight browser navigations not certified locally.
- Initial browser attempts lacked the default browser binary or local_dev directory.
  Retried the unchanged files with installed Chromium and the directory CI already
  creates: the same eight navigations returned ERR_BLOCKED_BY_ADMINISTRATOR.
  Both failed runs are retained; no policies, tests or thresholds were bypassed.
- Final core repetition: 243 PASS, already included in the 354 (do not add counts).
- 500 fixed-clock synthetic differential records match the original output; zero
  differences. These are supplementary cases, not 500 additional unit tests.
- Tests cover a single truth evaluation per accepted match, unchanged public schema,
  token bounds/Unicode/unhashable inputs, mutable output independence, mixed clocks
  across threads, missing/invalid evidence, terminal conflicts and LIVE expiry.
- Python compilation and Madrid checks pass. Existing Secret Guard scanned 1203
  files, zero findings, without exceptions or changes to the scanner.

## Paired local measurement, not mobile or production

200 synthetic DB records, 15 warm request pairs per route, randomized variant order,
Flask test client, no profiler/network/cron. Python 3.13.5. Same record counts and
snapshot output at a fixed clock; zero attempted external connections.

| Route | PR62 median ms | Candidate median ms |
| --- | ---: | ---: |
| / | 54.427 | 36.096 |
| /calendar | 104.244 | 71.412 |
| /live | 58.174 | 39.592 |
| /picks | 69.767 | 43.487 |
| /api/realtime/sports | 11.362 | 11.152 |

The four HTML medians decreased 31-38% in this sample. The warm API median changed
only 1.8%; that difference is too small to present as a robust gain. Its sampled
maximum increased from 11.741 to 14.239 ms. All raw observations are retained.
These numbers must not be added to PR62 percentages or compared across machines.
They do not show that the 15.5-second production navigation has been resolved.

The local distribution may omit optional blueprints; required remote QA, Preflight
and complete Smoke must run over the full repository and their normal Python versions.
The pre-existing mixed line endings in the realtime state module are normalized to
LF; reviewers should inspect the whitespace-insensitive diff as well as exact bytes.

## Release constraints

Do not interrupt PR62's in-progress production observation with another main merge.
Require all checks on the exact candidate HEAD. Preserve the old failed production
report, keep #61 open and measure actual post-deploy behavior before claiming success.
No concurrency configuration has been changed or certified. Queueing during cron,
resource transfer, browser rendering and the prior 502s remain separate open work.
Highlights, historical recovery and mobile/PWA candidates are not bundled here.

# P0: less repeated work on public sports reads

Base: PR58, `614dd35b2eb605a24149067ce999732c49d7cff8`.
Related issue: #61. This is a performance remediation candidate, not proof that production latency is fixed.

## Product changes

The existing sports cache still has one builder per key, the same TTL limits, force semantics and isolated per-caller graphs. Exact built-in dict/list/scalar graphs now use a scoped copy routine; other types use standard deepcopy with the same memo. No JSON conversion, global monkeypatch, loss of datetime/zero values or shared mutable cache data.

Copies run outside the global cache-index lock. Cache entries are privately owned and replaced, not mutated. Per-key generations prevent a builder that overlapped an invalidation from republishing its old view. Its already-running caller may finish that isolated point-in-time view; the next request rebuilds. Prefix invalidation also covers an in-flight key with no stored entry. Provider clocks are not renewed.

The realtime projection skips identities that were already accepted from a preceding section. Invalid first rows still allow a later valid row; existing first-valid precedence is unchanged. Sports Truth remains authoritative and LIVE expiry is evaluated at the requested clock.

## Local evidence (SIMULATED_QA)

57 new regression tests pass. The broader 303-case run had 295 PASS and 8 browser cases not certified locally. Five were blocked by browser navigation policy; three first required the existing `data/local_dev` setup, then were also blocked with ERR_BLOCKED_BY_ADMINISTRATOR. Both results are retained. No browser policy, tests or CI thresholds were changed.

Comparative deterministic probes against the original module:
- 25 identities in three overlapping lists: original normalized 75 times; candidate 25, with the same 25 LIVE results.
- An independent cache read could not finish while the original held the global lock for a paused copy. It completes before releasing that pause in the candidate.
- Invalidation during an old build: the original returned an old cache hit to the next request; the candidate rebuilt the new revision.

Final paired benchmark: 200 synthetic SQLite matches, 10 carrying current LIVE evidence; Flask test client, Python 3.13.5, no browser/network/cron load. 15 warm samples per version and route, randomized order, no profiler. Median milliseconds:

| Route | Original | Candidate |
|---|---:|---:|
| / | 90.962 | 66.480 |
| /calendar | 183.466 | 149.686 |
| /live | 100.981 | 84.451 |
| /picks | 122.878 | 85.690 |
| /api/realtime/sports | 22.495 | 15.285 |

35 paired copies of the same actual synthetic summary: median 26.099 ms for deepcopy and 8.361 ms for clone_snapshot. Fixed-clock snapshots and displayed counters matched. External connection attempts: zero. Earlier series also improved but varied; the figures above are the final run, not the best run. Raw samples and the initial profile are preserved in the conversation evidence package. Empirical sample p95 is descriptive, not a production percentile.

Reproduce using two local source checkouts with dependencies installed:

```sh
python tools/benchmark_snapshot_reads.py --baseline-root ../baseline --candidate-root . --output-dir ../local-evidence
```

The benchmark uses a new temporary database and denies socket connections. The source distribution used locally may omit optional blueprints; remote CI must run on the full repository and Python 3.11.

## Integration gate and remaining work

Require complete QA, Preflight and Smoke on the exact uploaded tree. This candidate does not change app.py, SQL/schema, production data, user permissions, provider calls, TTLs, CSS, workers, plans, credentials, payments or Telegram. It does not integrate PR59, PR60 or earlier cumulative packages.

The performance failure and isolated 502s in #61 remain unresolved until production evidence is re-measured. Do not close #61 based on local timings or promise instant navigation. A normal merge of the verified performance remediation may trigger the existing Render Auto Deploy; do not duplicate it manually. Verify the deployed SHA and retain post-deploy observation without cancelling it with another merge. Concurrency with cron, transfer/render costs and actual mobile latency still need separate measurements.

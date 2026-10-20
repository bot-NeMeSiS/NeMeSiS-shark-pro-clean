# Backup stage attribution correction — 2026-10-18

## Production evidence (read-only)

Natural backup attempts observed on 2026-10-18 between 04:30 and 06:30 Madrid all failed; 24 attempt records were seen. The stage stream recorded 24 `INTEGRITY` failures and 24 cleanup failures. Sample `INTEGRITY` durations were approximately 112–130 seconds. Cleanup events did not expose a cause, so the cleanup failure remains unexplained.

Source inspection showed that the non-compact SQLite `source.backup(...)` call ran after the stage had already been labeled `INTEGRITY`, while `PRAGMA integrity_check` ran later in the same stage. Therefore the observed `INTEGRITY` duration cannot identify which operation consumed the time. It does not establish corruption or prove that `integrity_check` was the slow operation.

## Local correction

Moved the `INTEGRITY` stage transition to after the non-compact snapshot operation. This preserves the backup algorithm, timeout, integrity verification, hashing, manifest, and publication behavior; it only assigns elapsed time to the operation that is running. Added a regression test that delays SQLite snapshot creation and verifies that the delay is reported under `SNAPSHOT`.

## Validation

- Focused backup suites: 36 passed, 1 skipped.
- `py_compile`: passed for the changed Python files.
- `git diff --check`: passed.
- The broader local test environment lacks Flask, so this result is not a full-repository certification; the complete CI suite must validate the change before release.

## Remaining limits

This change improves diagnosis; it does not fix or certify the production backup timeout. The cause of the long operation, cleanup errors, and any persistent SQLite or filesystem issue remains undetermined. No production backup, cleanup, or recovery was invoked, and no production data was changed. The next natural backup result is still required to confirm the corrected stage timings in production.

## Read-only follow-up — 2026-10-20

The current `main` commit `fc2b95b5` was observed LIVE in Render. The public runtime endpoint briefly returned 502 during instance replacement; a subsequent read-only check returned HTTP 200 from `/api/health`, `/api/runtime-version?compact=1`, and `/app`. This was a brief deploy transition, not an ongoing outage.

The natural backup window produced 24 `CAPACITY` failures, one at each five-minute tick from 04:30 through 06:25 Europe/Madrid. Each response was HTTP 200 from the backup endpoint, but `backup_created=false`; the Cron correctly recorded the domain result as failed. Across those attempts, required space ranged from 999,959,347 to 1,004,172,083 bytes, while reported free space ranged from 917,807,104 to 927,117,312 bytes, a shortfall of about 73–86 MB. No old copy was removed and no abandoned workspace was recovered. Both `CAPACITY_PREFLIGHT` and `COMPACT_CAPACITY_PREFLIGHT` rejected; the compact preflight took 2–8 ms (the capacity preflight took 2–11 ms), so these observations were capacity rejections, not 90-second snapshot timeouts. The compact-candidate measurements were not included in the current Cron summary, so these logs cannot yet distinguish insufficient reusable SQLite pages from an insufficient compact target margin.

After the window, the 06:30, 06:35, and 06:40 Madrid ticks reported `SKIPPED_NOT_DUE`; that is not evidence of a backup. No new certified SQLite copy was observed today. This result does not explain the separate timeout history from earlier dates.

### Local diagnostic improvement

The current local patch adds a bounded `reason_code` to the compact-capacity preflight and carries its available size measurements into the sanitized Cron summary. Allowed outcomes are `READY`, `NO_REUSABLE_PAGES`, `INSUFFICIENT_SPACE`, and `CAPACITY_CHECK_FAILED`; missing numeric values remain null rather than being reported as zero. Paths, table data, and exceptions remain excluded. The patch changes reporting only; it does not make capacity available or certify backup/restore.

The next natural backup after this patch is deployed must be read to distinguish the compact-copy limit. Production disk, quarantine, persistent data, and job invocation remain untouched.

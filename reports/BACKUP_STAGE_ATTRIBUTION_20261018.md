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

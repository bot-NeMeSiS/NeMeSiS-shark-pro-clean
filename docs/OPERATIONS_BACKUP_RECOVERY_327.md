# Issue #327 — operator-only recovery of SQLite (not automated)

## Why this exists

Production stores the real SQLite DB on Render Web's persistent `/data` disk.
On 2026-11-01, the DB snapshot estimate was about 1.80 GB and the disk
reported about 6.35 GB free. Automatic snapshots repeatedly aborted at
the **shared 15-second deadline** within `SNAPSHOT`. Increasing disk size
to 8 GB fixed capacity pressure, **not** the backup deadline.

Render Cron is a separate service and **does not have access to Web's
persistent disk**. Invoking the Web's synchronous backup API with a much
larger timeout can kill the default Gunicorn worker, so don't use that as
a workaround.

This script is an **operator-only recovery bridge**, not a repair of
the unattended daily backup. It must run on the Render Web shell, not
on the separate Cron shell, and is NOT invoked by an HTTP request.
Production deployment and the shell execution require operator approval.

## Safe run sequence

1. Confirm Web and Cron identity and health, and that `DB_PATH` points to
   the expected persistent DB. Review free disk space. Prefer a quiet
   traffic window; do not run another backup simultaneously.
2. From the repository root **on the Render Web shell**, execute a
   read-only capacity check:

   ```bash
   python tools/backup_operator_recovery_327.py
   ```

   It creates no files and returns `READY` only when enough space is
   available for both the snapshot and an **isolated restoration test**.
   The source defaults to `DB_PATH` or `/data/database.db`; a missing source is refused. Review any nonzero exit
   before proceeding.
3. After the readiness check and operator approval, run:

   ```bash
   python tools/backup_operator_recovery_327.py --execute
   ```

   This calls the existing atomic Data Vault backup with a dedicated
   900-second **shell-only snapshot-stage** budget. A separate verification budget starts before manifest, hash and SQLite
   integrity validation and covers the isolated restoration and schema check.
   Snapshot and verification have separate budgets; this is not a whole-command timeout.
   `preserve_existing_backups=True` prevents capacity reclamation as well
   as final retention, even if free space drops after preflight. It saves a DB and manifest with SHA-256 under
   `/data/backups/operator_327/` (unless `DATA_BACKUP_DIR` is explicitly
   configured). The source SQLite connection is read-only.
4. Success requires **all** of: `backup_created=true`,
   `code=RESTORE_VERIFIED`, `isolated_restore_ok=true`, a SHA-256 digest,
   and exit code 0. Verification first checks the manifest, SHA-256 and
   `PRAGMA integrity_check`, then copies the backup to a separate,
   disposable test database and checks its integrity and table schema.
   The disposable restore is deleted; the original database is never
   overwritten or restored into.
5. To re-check a backup already created without writing another one:

   ```bash
   python tools/backup_operator_recovery_327.py --verify-existing database_YYYYMMDD_HHMMSS_<id>.db
   ```

   Use the actual name printed by the successful command. The tool does
   not accept relative traversal paths as a backup name.

## Safeguards and unresolved work

- Never paste, email or publish DB snapshots: they contain private user,
  session and business data. Restrict shell and backup-directory access.
- The CLI refuses insufficient space; the dedicated directory avoids
  pruning ordinary backup history. All prior published and orphan archives
  are preserved by the explicit preservation mode, independently of
  `max_files`. If space drops, the tool fails safely instead of reclaiming them. If capacity changes during
  a long operation, the underlying Data Vault still protects its own
  staging and archive format; inspect any failure report carefully.
- An interrupted command is **not** a validated backup. Keep the current
  `main` database intact and inspect the archive after failures.
- A single verified manual recovery does **not** close #327. Still need
  two independently verified recent copies (or one tested external
  encrypted copy plus local recovery), an off-host retention policy,
  actual root-cause analysis of DB growth and a working unattended
  schedule independent of the Web request's 15-second budget.
- Keep Revenue OS #326 deployment gated until durable recovery exists.
  Do not merge/deploy as part of a backup drill without explicit review.
- This tool makes zero changes to Stripe, Telegram, API providers,
  memberships, cron configuration, server resources or secrets.

## Local synthetic test

```bash
python -m pytest -q tests/test_backup_operator_recovery_327.py tests/test_backup_preserve_history_mode.py tests/test_backup_validation_deadline.py
```

## Explicit write intent and remaining deadline limit

Without `--execute` or `--verify-existing`, only source metadata is read;
no snapshot or restoration file is created. SQLite itself can use its normal
shared-memory sidecars when reading a WAL database. `--verify-existing`
explicitly requests verification and writes a disposable isolated restoration,
but does not capture the live database or publish another backup.

Verification checks only the named archive, not the entire backup catalogue.
Its monotonic deadline starts before manifest/hash/integrity work and is
shared by restoration, restored integrity and full schema comparison. An
expired budget cannot yield `RESTORE_VERIFIED`; SQLite interruption from
that deadline is distinguished from I/O and integrity failures.

This is a cooperative budget at I/O boundaries and SQLite progress callbacks,
not an OS watchdog that can preempt a stalled filesystem syscall. Preflight,
snapshot and verification are not one hard whole-command timeout. The daily
automated 15-second path is unchanged and requires a separate fix and
natural-run evidence. A per-directory OS lock covers verification/restoration;
concurrent maintenance returns `RECOVERY_LOCK_BUSY` without creating a restore.

The bounded named validator requires a regular, non-linked SQLite archive
and a matching regular JSON manifest (at most 128 KiB) with valid=true, exact
size and full SHA256. Schema comparison includes every sqlite_master row
(type, name, table, SQL), rather than only the number of tables. No user rows
or secret values are printed. Previous archives and live data remain intact.

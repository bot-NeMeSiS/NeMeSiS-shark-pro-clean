# Issue #327 — operator-only recovery of SQLite (not automated)

## Why this exists

Production stores the real SQLite DB on Render Web's persistent \`/data\` disk.
On 2026-11-01, the DB snapshot estimate was about 1.80 GB and the disk
reported about 6.35 GB free. Automatic snapshots repeatedly aborted at
the **shared 15-second deadline** within \`SNAPSHOT\`. Increasing disk size
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

1. Confirm Web and Cron identity and health, and that \`DB_PATH\` points to
   the expected persistent DB. Review free disk space. Prefer a quiet
   traffic window; do not run another backup simultaneously.
2. From the repository root **on the Render Web shell**, execute a
   read-only capacity check:

   \`\`\`bash
   python tools/backup_operator_recovery_327.py
   \`\`\`

   It creates no files and returns \`READY\` only when enough space is
   available for both the snapshot and an **isolated restoration test**.
   The CLI won't run when \`DB_PATH\` is absent. Review any nonzero exit
   before proceeding.
3. After the readiness check and operator approval, run:

   \`\`\`bash
   python tools/backup_operator_recovery_327.py --execute
   \`\`\`

   This calls the existing atomic Data Vault backup with a dedicated
   900-second **shell-only** budget and \`max_files=0\` to disable automatic
   retention. It saves a DB and signed-by-hash manifest under
   \`/data/backups/operator_327/\` (unless \`DATA_BACKUP_DIR\` is explicitly
   configured). The source SQLite connection is read-only.
4. Success requires **all** of: \`backup_created=true\`,
   \`code=RESTORE_VERIFIED\`, \`isolated_restore_ok=true\`, a SHA-256 digest,
   and exit code 0. Verification first checks the manifest, SHA-256 and
   \`PRAGMA integrity_check\`, then copies the backup to a separate,
   disposable test database and checks its integrity and table schema.
   The disposable restore is deleted; the original database is never
   overwritten or restored into.
5. To re-check a backup already created without writing another one:

   \`\`\`bash
   python tools/backup_operator_recovery_327.py --verify-existing database_YYYYMMDD_HHMMSS_<id>.db
   \`\`\`

   Use the actual name printed by the successful command. The tool does
   not accept relative traversal paths as a backup name.

## Safeguards and unresolved work

- Never paste, email or publish DB snapshots: they contain private user,
  session and business data. Restrict shell and backup-directory access.
- The CLI refuses insufficient space; the dedicated directory avoids
  pruning ordinary backup history. All existing historical archives are
  preserved by the configured \`max_files=0\`. If capacity changes during
  a long operation, the underlying Data Vault still protects its own
  staging and archive format; inspect any failure report carefully.
- An interrupted command is **not** a validated backup. Keep the current
  \`main\` database intact and inspect the archive after failures.
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

\`\`\`bash
python -m pytest -q tests/test_backup_operator_recovery_327.py
\`\`\`

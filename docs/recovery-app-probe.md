# Isolated recovery: guest App verification

This is an operator-only diagnostic. Flask and Cron do not call it. Publishing
the code does not authorize or execute a real capture, restoration or download.
An existing specific data-operation authorization must cover the operation.

`backup_operator_recovery_327.py` preserves its SQLite-only default. The explicit
`--app-probe-mode normal_boot` option starts a fresh, bounded interpreter on the
**same disposable restoration**, after the archive/restore connections close and
before that workspace is removed. It does not create a second restoration. All
archive validation, integrity, schema comparison and final identity checks remain.
The App shares the existing verification deadline; no budget is restarted.

`normal_boot` imports the complete real App and exercises guest Calendar, Home,
Picks, SHARK, Team and Search. Genuine initialization may write only to the
disposable database, its journals, the copied source's `data` directory and
scratch. It does not pre-set initialized flags, replace business getters or seed
fixtures through substituted App functions. Network, other databases, background
threads and additional processes are rejected. Boundary denials abort the probe;
App fallbacks cannot convert them to success.

`--app-probe-mode read_only` is a different diagnostic. Its actual SQLite
connection uses the same restoration with a read-only capability. Initialization
and write attempts remain failures. It is expected to reject cold routes that
require migration/initialization; this does not prove that normal recovery failed.
Each explicit invocation has one mode and one restoration. Running two invocations
would create two restorations and requires the corresponding authority.

The guest verdict requires HTTP 200, actual completed SQLite read execution and
fetch, no observed unavailable storage state, no degraded-route handler and no
boundary denial. Search must report READY and complete, including a valid empty
result. Normal boot also requires genuine initialization without an init error.
The report counts authorizations separately from completed reads and retains no
SQL, result rows, credentials, page bodies or App log contents.

Source copying admits application code/assets from closed directories, excludes
runtime/backups/reports and secret-like filenames, limits files/bytes and rechecks
identities. POSIX opens traverse no-follow directory descriptors; Windows rechecks
ancestors and the opened descriptor before any content read. This is confinement
for this fixed trusted probe, **not a sandbox for arbitrary Python or an assertion
that source code cannot contain embedded secrets**. Copied source digests identify
the observed files; they are not independent Git/deployment attestation.

The child uses at most the configured process memory budget (default 256 MiB):
POSIX `RLIMIT_AS` preserves lower inherited limits; Windows bounds aggregate job
commit, including its venv launcher. These limits are not RSS measurements or a
Render resource reservation. The Render preflight fails closed without adequate
observable headroom. Additional restore capacity includes source/scratch and, for
normal boot, a full journal allowance. The parent's source-copy deadline remains
cooperative; the child process has an enforced wall timeout. Unsupported long
Windows workspace paths are refused before copying or launching.

The child deliberately uses the already-declared `tzdata` package for UTC/Madrid
through the standard `zoneinfo` path configuration, with caches cleared before
App import. This avoids admitting filesystem symlinks merely because some Linux
timezone aliases use them. No timezone object is prebuilt before the guard. The
receipt records the installed data version; this is an isolated probe input,
not attestation of production's OS timezone source. Link/secret guards remain.

`SQLITE_RESTORE_AND_GUEST_APP_SMOKE_VERIFIED` is deliberately narrower than full
recovery. It does **not** certify authenticated client/Admin sessions, secrets and
configuration custody, external providers, Telegram, payments, automation,
non-SQLite state restoration, browser layout or production. Owned synthetic tests
do not certify a real backup. Full recovery remains false in these receipts.

The recovery inventory separately recognizes the producer-defined Sentinel issue
ledger and closed derived evidence/history paths. Locks remain transient;
unknown/private entries remain opaque and incomplete. Metadata-only mode reports
file kind/link count/size for admitted opaque names without reading content.
Inventory limits (400 entries, depth 6, 16 MiB hash budget, five seconds) remain.
An inventory, source digest or successful guest smoke never replaces backup
integrity, hashes, manifests, atomic publication or a real authorized restore.

# CompanyOS scheduler lock protocol

On POSIX the scheduler uses a nonblocking `fcntl.flock` held by an open file
descriptor throughout execution. The JSON marker records `lock_protocol`, job,
PID and time. Native review requires the current process's registered descriptor,
matching marker and unchanged regular-file inode, rather than JSON alone.

The marker is never unlinked on release. Closing the descriptor or process death
releases the OS lock; the next protocol-aware process can reuse that same inode.
Fork children close inherited descriptors without `LOCK_UN`, so they cannot
release the parent's ownership or keep it alive after the parent exits. The
descriptor is also close-on-exec. Existing due checks, attempt deduplication,
budgets and static-only certification flags are unchanged.

## Conservative migration and rollback

An existing legacy or malformed marker is preserved. Acquiring advisory flock on
it cannot establish that an older exclusive-create owner has stopped. Therefore
this change does **not** clear the current legacy `STALE_LOCK`, migrate its state,
or demonstrate 22/22 production review. Any one-time legacy recovery needs its
own verified owner-cessation evidence and specific authorization. No such
operation is part of this patch.

Without POSIX flock, the previous conservative exclusive-create behavior remains.
Windows tests do not establish Linux or deployment-filesystem lock semantics.
Linux CI exercises independent contenders, abrupt process exit, fork ownership,
legacy preservation, symlink/hardlink rejection and native ownership guards in
disposable directories. It does not probe production storage.

Reverting the code preserves all receipts and marker files. Older code treats a
remaining protocol marker conservatively as an existing lock; rollback may stop
further scheduled reviews until a separately authorized transition. Reversion
must not delete a marker to force progress. No database migration, backup,
restore, cleanup, resource change or new service is included.


## Explicit one-use legacy transition operator

`tools/companyos_legacy_lock_transition.py` is a manual operator, not a job,
route, scheduler hook or automatic migration. Its default operation is a
read-only plan. Importing it never imports App, connects to SQLite or starts
workers. Publishing this code does not authorize or execute a data operation.

Prepare the expected JSON from fresh read-only metadata after the candidate is
actually deployed: runtime SHA and instance, storage-root device/inode, and
marker device/inode/mtime_ns/SHA256. All eight fields are mandatory. The tool
does not accept an old prompt SHA as evidence of the current version. It rejects
context changes, ancestor symlinks, changed roots, nonregular/hardlinked markers,
malformed markers and markers that already use the new protocol. It reads at
most4096bytes from the legacy marker and does not print its job_id.

An eventual `--execute` requires both `--cessation-reference` and
`--authorization-reference`, referring to an externally reviewed owner-cessation
record and a NEW specific human decision for this exact operation. These strings
are audit references, not authentication, proof or permission granted by code.
The tool is not an authorization ledger: the operator must check that the native
decision is current and unconsumed, record the outcome and never reuse it for
a retry or rollback. The tool does not verify reference IDs or grant single-use
authority itself.
PID absence/reuse, age, an unlocked advisory flock and a reference string alone
cannot establish cessation. Review the actual disk/service ownership, deployed
protocol, instance replacement and any remaining concurrency uncertainty first.
Do not execute while that gate is unresolved.

After those external preconditions are satisfied, the operator takes a
nonblocking flock only to exclude protocol-aware competitors, rechecks the
exact identity/content and atomically renames the legacy file beside itself as
`scheduler.<inode>.<sha256>.legacy.json`. Linux `renameat2(RENAME_NOREPLACE)`
prevents overwriting an existing preservation file. Both names are anchored to
the same verified directory FD; the original inode, bytes and mtime remain (ctime may change).
No file is unlinked, rewritten, copied or deleted. A standard Python
`os.rename` audit event with absolute source/destination is emitted BEFORE the
native syscall, preserving the existing LOCAL_SAFE supervisor's veto. There is
no fallback to an overwriting rename if the primitive is unavailable.

The original file is fsynced before the rename. The parent directory is fsynced
and the preserved identity/content are checked
again. Failure after the rename reports an incomplete postcheck and requires
review of the same attempt; it never retries or silently rolls back. Preserve
the original and any resulting receipt/artifact in every failure case.

The next execution is the existing natural schedule only. This transition may
allow an already-scheduled caller to proceed immediately after the atomic name
change; that effect must be included in the specific human decision. The
operator never invokes a scheduler, backup, restore, provider, Telegram or a
worker. A completed static workforce review still cannot certify business
execution, 22activeworkers or authenticated Admin visibility.

`--rollback`, under its own reviewed decision/reference, only renames the exact
preserved legacy inode back if `scheduler.lock` is absent. A new marker of any
kind causes an atomic no-replace refusal, even if it appears just before the
syscall. It never overwrites or releases a new owner. If the next natural run
has created a protocol marker, preserve both states and review a separate
owner-safe reversal; do not delete the new marker to force rollback. Reverting
code remains conservative and does not authorize marker deletion.

Linux CI must establish actual confined/no-overwrite rename, flock exclusion,
exact preservation, default read-only behavior, audit denial, identity drift,
symlink/hardlink rejection, collision and rollback behavior in disposable
directories. Windows input-validation tests do not establish Linux semantics.
Neither tests nor a generated plan certify the production filesystem or grant
permission for the current legacy marker.

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

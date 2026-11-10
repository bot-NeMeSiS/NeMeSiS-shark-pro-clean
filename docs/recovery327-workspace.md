# Optional isolated restoration workspace (#327)

This code adds no scheduled caller, web endpoint, capture permission or real
recovery certificate. Production remains read-only unless an exact future data
operation receives its own current authorization. The CompanyOS marker
preservation permission was consumed and is unrelated to backup/restore.

## Defaults and explicit selection

Without --restore-workspace-root, the existing archive-directory temporary
restoration remains unchanged. The optional argument selects a pre-existing,
absolute Linux directory. It does not create that root, change environment or
services, reserve space, resize a disk or grant permission.

The root and ancestors must have no symlinks/reparse points, be owned by the OS
or current user, and not allow other-user writes except trusted sticky
directories. Archive/source tree overlap and equal root identities are refused.
The operator binds device/inode before its preflight, rechecks before capture
and passes that SAME identity into restoration. Root drift stops the operation;
it never silently adopts another root or falls back to the archive disk.

This is confinement for a trusted fixed operator and fixed App probe, not a
sandbox against hostile same-UID Python or a host administrator. OS/filesystem
topology and actual permission/capacity still require a fresh reviewed plan.

## Capacity and custody

The SQLite/state publication and manifests remain in the original durable
archive directory. The temporary root contains ONE restoration-test.db, the
owned source mirror, extracted state and App scratch/journal. It is not custody,
an independent backup or off-host storage.

Preflight keeps capacity by actual filesystem device. Free space from a
different filesystem cannot pay for durable publication. Two observations on
the same device use the lower free value, not two copies of the same pool.
The normal-boot journal, source/scratch allowance, state archive and extracted
state remain included. The existing typed-state preflight uses the same model.
This calculation is an estimate, not a reservation or memory feasibility proof.
After publication, phase B measures workspace capacity again against actual
archive size and the existing bounded state limit.

## Identity, creation and cleanup

On Linux, creation and cleanup use a held directory descriptor through the
process's own /proc/self/fd reference. All mutations use ordinary audited Python
mkdir/unlink/rmdir calls. No native-syscall bypass, cwd change, audit-hook change
or extra subprocess grant is added. The App continues to receive ordinary
private workspace paths and its unchanged original guard.

The created child is unique, mode0700 and identity-checked. Only that child is
cleaned. Root/entry drift, an unexpected link/special file, audit refusal or an
exhausted deadline stops cleanup and conserves remaining scratch for review;
it never recursively deletes a replacement tree or follows an external link.
There is no automatic retry, reclamation task or cleanup of another workspace.
Unsupported platforms/procfs fail without fallback.

## Timing and SAME restoration

The optional root creates no new phase or deadline. Existing aggregate phase A
and aggregate phase B remain distinct; the reviewed real-data contract remains
A300s/B300s, with automatic backup15s unchanged. Hash, full integrity, standalone
archive identity, manifest and atomic publication are unchanged.

Phase B validates the archive, creates ONE isolated SQLite restoration, verifies
it, and passes that SAME restoration and SAME deadline to the explicit guest
App probe. New workspace cleanup also uses the caller's existing deadline; it
cannot obtain another budget. normal_boot may initialize only the disposable
clone. read_only is diagnostic and must not be substituted to bypass normal
boot failures. --verify-existing still creates a disposable restoration and is
not a production read-only command.

## Limits and verification scope

Owned Linux filesystem/SQLite tests cover root drift before/after publication,
audit veto, no fallback, private child identity, links, cleanup, shared budgets
and preservation of durable archives. The original LOCAL SAFE loop exercises
the new planning/backend files. The actual SAME-restore/guest App case and
legacy default regression run in the existing standard suite, using the
unchanged native App guard; no new process authority is added to LOCAL SAFE.

A passing synthetic guest probe is not a current real-data recovery proof,
authenticated Admin/client recovery, all worker execution or a complete
platform certificate. Auxiliary SQLite generation consistency, complete CE/
runtime inventory, secret custody, memory and an exact approved integral data
operation remain gates. No unknown store may be excluded to make this feature
look complete.

Successful explicit-root verification reports actual root/device/inode,
SAME-restoration use for the App and completed owned cleanup. Failure can report
that scratch may be preserved; absence of a success field is not verification.
These receipts do not certify reserved space, memory, off-host custody or the
full platform.

When an explicit owned child was created, failure receipts retain its generated
name and observed identity so remaining scratch can be reviewed without
claiming cleanup succeeded. A name/identity receipt is evidence, not a new
cleanup authorization. An interrupted process without a terminal receipt
remains unverified; absence of a receipt never permits retry or deletion.

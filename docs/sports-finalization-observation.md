# Sports finalization: exact counts and bounded observations

The natural 2 November 18:10 UTC Sports request timed out at the Cron transport
after 24.079s. The web access log subsequently recorded HTTP200 at18:10:52.841UTC.
The last existing grading measurement ended at18:10:35.834UTC. Neither the late
HTTP200 nor the following successful tick identifies the missing delay or proves
that the client received the response.

Sports now reuses the existing closed operational timing engine for its route
handler and nine post-grading boundaries. Labels and error categories are fixed;
payloads, SQL, accounts and sporting identifiers are excluded. Parent totals and
child phases overlap and must not be added. An end record reports whether an
exception escaped that block, not whether an internally caught write succeeded.
`response_json` measures serialization; the operation ends on handler return,
before Flask after-request/teardown and WSGI delivery. Missing end observations
must remain missing. Stdout is synchronous and has no hard backpressure bound.

The account summary retains its exact counts, filtering, tables and diagnostics.
Only the tautological `WHERE1=1` is omitted, allowing SQLite's native count
operation instead of per-row aggregation. A700000-row owned, minimal-payload
fixture returned the same count, with1400 versus zero callbacks per1000VM
instructions, and0.063s versus0.016s in one local observation. This demonstrates
unnecessary SQL work; it does not explain17s on Render or certify cold performance.

No deadline, provider call, transaction, public response, quota or worker schedule
is changed. No interruption handler is added: the historical summary error-to-zero
fallback requires a separate truthful unknown/deferred contract before such a
change. Observer clock/trace failures cannot replace a business result or error.

This release is an intermediate corrective and diagnostic step. Sports timeout
resolution remains unproved until the causal boundary and affected full request
are observed and corrected. Recovery of real data remains a separate incomplete
priority; no backup, restoration or download is authorized by this code.

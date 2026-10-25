# V993 — expired-data feedback and operational attribution

Directo's first server response now identifies expired observations even when
the canonical summary already excluded those rows. It displays the existing
localized stale-data notice instead of presenting that state as no live events.
Expired observations do not regain a score, minute, LIVE approval or lease.
Fresh, verified-empty and unavailable-read contracts retain their own meanings.

Media and Postmatch record closed, request-local phase timings to investigate
the observed Media timeout and Postmatch SQLITE_BUSY episode. Random technical
trace IDs correlate nested Media collection with its receipt write, and separate
Postmatch connection, BEGIN, read, enqueue, commit and rollback boundaries.
Logs contain no SQL, paths, match/user IDs, provider URLs, payloads or exception
messages. Observer failures preserve business results and original exceptions.
Captured transaction events are buffered within a bounded trace until the
observed connection releases its transaction; offsets preserve capture timing.
Media's two run-ledger connections close after their existing transactions.

This attribution does not claim to fix the unproven cause of the production
timeout or lock. Collection budgets, transport deadlines, SQLite wait settings,
reservations, rollback, rights, quotas, schema and automatic schedules are intact.
Future-date coverage, complete Media delivery, certified backup/restore and the
remaining platform acceptance gates stay open until their own evidence closes.

Tests and publication state belong to the dated operational checkpoint.

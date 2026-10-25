# V992 — current fixture admission

On a dense matchday the bounded public read could select hundreds of early
finished fixtures and exclude every recently updated live fixture, even when
the provider snapshots were correctly mirrored into the matches table.

Within each current/upcoming date, the same read now admits nominal LIVE and
scheduled candidates before other statuses. Existing update-order evidence
breaks ties between LIVE candidates before kickoff order. Dates retain priority;
the read limit stays 800 and the separate historical results path stays unchanged.
No row, result, provider observation or clock is rewritten by this selection.

Status is an admission hint only. The existing lifecycle, source freshness,
operation ownership, native identity and C3 checks still determine whether an
admitted row can be displayed as live. P (live penalties) remains distinct from
PEN (finished after penalties). Older schemas without a status column retain
their previous ordering. No provider requests, quotas, plans or timeouts change.

This corrects admission within the bounded snapshot. It does not promise a
complete future calendar when today's rows alone exceed that limit, or certify
backup, delivery, all provider coverage or global production stability.

Local and CI results, publication SHA, runtime alignment and natural production
observations are recorded separately in the dated operational checkpoint.

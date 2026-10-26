# V994 — retain current LIVE observations across Madrid midnight

The bounded shared reader now admits recent LIVE candidates from today and the
earlier Madrid dates before filling the current/upcoming calendar window. This
prevents a dense future schedule from hiding a still-active previous-day match.
This also retains a resumed match with an older original date when its own LIVE
evidence is still current. Match dates, scores, clocks, native IDs and stored rows are kept.

Admission uses the existing canonical provider-clock field precedence and
freshness/skew constants, with a one-second selection margin for whole-second
age rounding. It is not LIVE authorization: the existing native identity,
lifecycle, conflict and freshness checks still determine what customers see.
No LIVE lease is extended. Stale observations, future dates and generic updated_at alone
do not gain this priority. The 800-row bound, ordinary date order, historical
read path, source truth and non-match readers remain in place.

The selection_policy diagnostic names the new ordering when supported by the
existing schema. No schema, provider call, quota, deadline, permission, data
cleanup, disk size or service configuration changes are introduced.

This corrects admission, not unlimited calendar coverage or global latency.
Media queue optimization, certified backup/restore and platform-wide acceptance
remain separate open work. Publication and final test evidence are recorded in
the dated operational checkpoint.

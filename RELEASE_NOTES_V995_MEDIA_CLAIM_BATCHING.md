# V995 — Select historical highlight work without parsing the whole queue

The historical Media claim query previously evaluated lifecycle and identity
against every candidate payload before sorting and choosing one. This held its
writer transaction while doing work unrelated to the selected match.

The claim now orders cheap IDs using the same filters and ordering, reads up to
64 full SQLite JSON projections at a time through existing primary keys, and
applies the unchanged eligibility and identity functions until the first valid
match. Invalid leading batches never end the search; a queue with no valid
candidate is traversed completely. The candidate cursor closes before the lease
update. Global lease exclusion, BEGIN IMMEDIATE, rollback and publication rights
remain unchanged. No schema/index, quota, deadline or provider change.

Tests compare the actual old SQL winner and payload with the new path, cover
batch boundaries, full invalid traversal, mixed lifecycle, optional fields,
priority/due/date order, independent concurrent claimers, and validation rollback
in both early and later batches. The dense selection test verifies that only the
selected candidate needs lifecycle/identity evaluation. Existing Media caching,
provider-budget and rights tests remain required gates.

The external 20,000-row synthetic prototype measured less selection work while
preserving the winner. Those timings are not Render benchmarks and do not prove
the cause or resolution of the earlier Media timeout/SQLITE_BUSY incident.
Published highlights still require actual provider evidence and valid rights.
Backup/restore and platform-wide acceptance remain separate requirements.

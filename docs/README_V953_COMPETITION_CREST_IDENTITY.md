# V953 — Competition crest identity

The competition standings now reuse an existing team crest by exact team ID
within the same provider namespace before trying a display-name fallback. This
supports provider spelling variants without confusing numeric IDs from different
providers. Exact-name fallback remains available only for one unambiguous team
in the competition context; a conflicting provider ID or duplicate identity
does not receive a crest.

The change reads only the already loaded standings and cached team context. It
adds no provider calls, database writes, identity merges, or schema changes.

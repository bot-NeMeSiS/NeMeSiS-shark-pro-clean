# V958 — Admin highlights lean read

The admin highlights page and status endpoint now read the highlights catalogue directly instead of constructing the full sports dashboard first. This removes unrelated request work while preserving the existing admin guard, catalogue truth states, rights counts, and pending-match summary.

No provider calls, writes, synchronization jobs, membership changes, or production data changes are introduced.

Validation: `tests/test_v958_admin_highlights_lean_read.py` covers both admin routes, confirms the full dashboard is not loaded, and checks that unauthenticated requests remain blocked.

# Highlights read consumers — 23/09/2026

State: DRAFT / NOT_DEPLOYED.

This increment closes two legacy read-path gaps without changing ingestion, providers, rights decisions, Telegram or production data.

- Canonical detail lookup now uses the read-only highlight model and never prepares media schema on GET.
- Calendar/result badges use one bounded read-only batch snapshot (max 500 match IDs) and preserve rights filtering.
- Missing/unreadable catalogue is UNKNOWN: counts stay null/unknown and UI says "Disponibilidad sin comprobar".
- Verified empty catalogue remains a valid zero.
- Client content center no longer exposes Render environment-key instructions as customer copy.
- Optional highlight detail catalogue unavailability renders a safe 200 informational page instead of a 5xx; verified missing/blocked media remains 404.
- Machine/admin diagnostics keep explicit unavailable states.
- No external provider calls, no media download/rehost, no rights expansion and no fake availability/playback claim.

Commits:
- 6f8d4b6f1798676550e8504bc5c1a897c54a8869 — read-only legacy consumers and truth propagation.
- 12b89e543ecba9c4e96038981b409e81acc84303 — client-safe unavailable detail response for Navigation Integrity.

New regression file: tests/test_highlight_legacy_read_consumers.py.
The previous Preflight failure on 6f8d4b6f was caused by the Navigation Integrity worker treating the new optional-detail HTTP 503 as ROTA_500, while its static audit still reported 0 broken links and 0 actionless buttons. The client route was adjusted rather than weakening the auditor.

No real video, production catalogue, rights grant or playback has been certified by this increment. Require QA + Preflight + Smoke of the exact final HEAD before any merge.

# V996 — Temporary SHARK workspace

SHARK is available through one logo-only floating launcher on client/public
surfaces. Its native dialog can expand, reduce, minimize, hide and restore from
Explore without replacing its transcript DOM. The compact empty state avoids a
large unused panel. Full-page SHARK routes and the useful GET link remain
available without JavaScript; Admin keeps its separate existing SHARK surface.
Only the SHARK primary client navigation item is removed; discovery stays intact
and the four remaining mobile items share the available width.

Questions use the existing authenticated POST, canonical CSRF and atomic plan
quota. UI-only operations make no SHARK request. A pending latch prevents double
submission; errors do not automatically retry a potentially charged question.
Untrusted answer text is rendered as text. Session/CSRF rejection clears private
DOM and prevents late responses from restoring it. Quota rejection links to the
existing membership page and preserves the draft.

Conversation is temporary to this document, without browser message storage or
invented backend history. Same-origin document transitions clear older panels,
including across tabs. This conservatively also clears on same-account
navigation in another tab. Restricted browsers without BroadcastChannel clear
on focus loss instead. Minimize/expand/hide/restore within the same page retain
the conversation. Page departure and restored-page handling clear it.

The existing brand assets, routes, provider/LLM behavior, rights, quotas and
permissions remain unchanged. Spanish, English and French control copy uses the
existing UI catalogue. CSS is built from the canonical source bundle. Isolated
actual-App/HTTP/JavaScript browser gates cover desktop/mobile, with explicit
fault fixtures distinguished from real server auth/quota checks.

This does not certify physical iOS/Android, all production account journeys,
continuous LIVE freshness, paid-provider quota, backup/restore or platform-wide
commercial acceptance. Those remain separate gates.

# Telegram Ultra Pro - isolated candidate, 2026-09-23

Status: RECONCILED_CURRENT_MAIN / CI_PENDING / NOT_DEPLOYED. No real Telegram messages sent.
Branch: codex/telegram-ultra-pro-20260923.
Original Codex base: 706094630d337f9e329a8401fae217b316a9b49c. Current reconciliation base: main@228369d42447f37f3023a7f09216205057e4655c. The original 226-pass local evidence is preserved as historical component evidence; fresh remote CI is required for this reconciled HEAD.

## Isolation and continuity

- The original Telegram patch was preserved in the Hygiene worktree and reused
  selectively on a new Git worktree based on current main. No repository copy.
- Hygiene remains at 70609463 with its previous dirty files unchanged.
- Founder remains at 79209330 with its two local modifications unchanged.
  HEAD, status and SHA-256 of their modified/untracked files match the initial snapshot.
- Local main remains 454c3ca1; it was not switched, advanced or reset.
- No PR60/68/72, Design, cron, provider, account or payment work imported.

## Defects corrected

- Previous visual engine had overlapping sections and limited type differentiation.
  Current cards use measured text, fixed bounds, coherent colors and plan identity.
- Missing data previously acquired generated stake/risk/value in delivery formatting.
  Presentation now distinguishes missing information and confirmed zero.
- Raw structured fields could appear as Python/JSON text. Scalar formatting rejects them.
- FREE presentation omitted available risk. Both existing presentation paths now retain it.
- A video URL alone previously enabled a highlight. Telegram now delegates to
  classify_media_asset with channel TELEGRAM, commercial-use and attribution checks.
- Existing team_logo_cache.local_path was not consumed. Exact URL mappings now reuse
  valid local raster images, without matching teams by an ambiguous name.
- Persisted visual delivery evidence was read at the wrong JSON nesting level.
  Preview now reads the real response envelope, delivery ID, source, Madrid timestamp,
  dedupe presence, visual generation and sanitized fallback/error details.
- Definite invalid-button rejection previously lost the message. A bounded text retry
  removes rejected buttons; uncertain responses/timeouts do not trigger a second send.

## Files and scope

- app.py: existing transport, queue payload, welcome, readonly preview and asset integration.
- engines/telegram_message_formatter.py: canonical Spanish copy, Madrid, safe HTML,
  captions, rights gate, grading and responsible/risk information.
- engines/telegram_visual_card_engine.py: five PNG variants, competition logo, local
  crest/cache handling, font reuse, measured names and resolution constraints.
- engines/telegram_delivery_engine.py: preserve ranking/filtering; remove invented filler.
- engines/telegram_activity_engine.py: canonical lifecycle/freshness and rights checks.
- engines/telegram_intelligence_engine.py: existing FREE preview retains risk, no new engine.
- templates/admin_telegram_pro_preview.html: existing admin page, responsive and readonly.
- tests/test_telegram_visual_premium.py: positive/negative regression and browser evidence.
- .github/workflows/nemesis-smoke.yml: run the new LOCAL SAFE tests in the existing
  isolated test stage, not the ordinary pytest process. No test disabled or skipped.

## Types, assets and fallbacks

Pick, combi, LIVE, result and highlight have visual variants. Agenda, reminder,
activity, day close and system/welcome retain premium text. Flags stay unchanged,
including LIVE card OFF by default. Plans/destinations and scheduling are not changed.

Team sources: explicit home/away logo fields; exact URL-to-local-path entries in
the existing team_logo_cache. League source: explicit competition/league logo fields.
PNG/JPEG/WebP below static only, with containment/reparse/size/pixel checks.
Remote URLs without valid local bytes and SVG use initials; no external download.
One missing/broken crest leaves the other intact. Whole-render/Pillow failure gives text.
Photo rejection may fall back to text only when failure is definite. Timeout/5xx or
unverifiable acceptance stays uncertain, not SENT and not automatically resent.
Existing sequential dedupe is tested; distributed exactly-once delivery is not claimed.

## Verification

226 PASS / 0 FAIL / 0 ERROR / 0 SKIP, 29.165 seconds.
This is the related suite, not the entire repository or a production certification.
Files: test_telegram_visual_premium, test_telegram_premium_communication_system,
test_v727_telegram_reliability, test_telegram_football_only_filter,
test_design02_global_madrid_time, test_madrid_greeting,
test_sports_media_rights_convergence, test_sports_knowledge_media_experience.

Flask and SQLite real, disposable storage. Telegram transport intercepted.
Boundary events: [] (no external connection attempted by QA).
Browser: Chromium 1366, 390 and 430 px; admin access, client rejection, readonly
GET, caption expansion, PNG download, Command Center and return. No JS errors/overflow.
AST/Jinja, diff-check and secret/privacy patterns on the scoped diff: PASS.
Source EOL formatting was preserved on unchanged app.py lines; normalized code
content is identical to the tested revision. No full-file formatting churn.

Positive/negative cases include both/one/no crest, corrupted image, Pillow/render
failure, photo rejection vs uncertain delivery, long names, Unicode/HTML, missing
odds, combi 2/3 legs, won/lost/void/pending, rights/attribution, FREE risk and stale LIVE.

Final QA: data/local_dev/candidate-d9c2835916224db482be78e8789166a5/result.xml.
External local evidence folder: telegram-ultra-pro-isolated-20260923 in the current
Codex visualization directory. scope.json records exact source hashes and QA totals.
SIMULATED_QA: five PNGs, text captions, long-name case, gallery and three browser captures.
All teams, scores, odds and QA badges in the gallery are synthetic, never enqueued.
No official crest is invented. The production preview uses stored payloads or honest empty states.

Five-render local sample: 146-219 ms/card; PNG 64-89 KB. Not P50/P95 or a load benchmark.

## Review and publication boundaries

Allowed next step in this mission: selective commit/push and one DRAFT PR to main.
No merge, deployment, environment change, provider call or real Telegram send authorized.
Before release: review draft/remote CI, supply approved locally cached assets where
needed, authorize a controlled send and inspect actual Telegram mobile/desktop clients.
No claim that card fidelity or destination permissions have been verified in Telegram.
PR workflow production certification runs only on main push/authorized dispatch,
not on this draft PR. No workflow or scheduler is activated manually here.

## Current-main reconciliation

- Rebuilt from `main@228369d42447f37f3023a7f09216205057e4655c` rather than merging the old PR history.
- The 19 `app.py` hunks from reviewed PR #77 matched exactly once against current main before application.
- Provider Health/direct-check and existing PWA changes remain present in the merged app bytes.
- No Telegram transport was invoked during reconciliation; no provider, payment, DB or Render action was executed by this candidate.
- Release remains blocked until exact-head QA + Preflight + full Smoke/LOCAL SAFE/Sentinel gates pass and the founder explicitly authorizes any real Telegram send or merge.

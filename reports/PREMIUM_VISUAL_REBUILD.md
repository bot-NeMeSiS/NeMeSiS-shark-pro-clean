# Premium visual reconstruction phase

Base: `main` at `acd74b175a677be8ce3b2a4ba87f9844e9591a11`.
Branch: `feat/premium-visual-rebuild`. PR #165 remains independent; no cherry-pick,
merge, reconciliation, season backfill, migration or production execution.
At verification #165 was open, mergeable, based on main, head
`8cbe4e6b746e351b87066d6ff16cc290ad7b0209`. All seven active workflow checks passed;
remote browser capture and deployment-only jobs were skipped.

## Changes

- One committed product CSS bundle replaces eight global stylesheet requests.
  The deterministic PostCSS/cssnano build preserves source order and removes
  redundant declarations/rules. Normalized source: 1,385,304 bytes; bundle:
  1,248,666 bytes (9.9% smaller). Node is a development dependency only.
- Edit existing tokens and component rules rather than add another override
  stylesheet: neutral surfaces, restrained SHARK blue, shared radii, softer
  shadows, consistent raised panels, aligned numeric scores/odds/KPIs.
- Match, pick, live, Team Center, Match Center, memberships, Telegram,
  account/support and command-center surfaces inherit the same primitives.
  Existing source modules and route-specific styles remain for compatibility;
  this phase does not claim that all historical selectors have been retired.
- Semantic success/warning/danger colors survive the cascade. ELITE+ receives
  a valid normalized class and its own purple accent. Client tiers use common
  structure with individual accent tokens.
- Sidebar quick actions fit their container; empty-state actions move below
  text in narrow panels. Home shortcuts use icons rather than text squeezed
  into small circles. Sports names no longer receive automatic hyphenation.
- Keyboard skip link, visible focus, reduced-motion handling, mobile touch
  sizes and a native account menu expose memberships and support.
- Fixed an existing invalid transition declaration found by the CSS parser.

Known pre-existing tier limitation: the presentation helper recognizes ELITE+,
but `app.normalize_role` and the entitlement engine accept FREE/PRO/ELITE/ADMIN.
A persisted `ELITE_PLUS` account therefore renders FREE after session
normalization. The ELITE+ visual class/accent is prepared and corrected, but this
phase does not introduce a fourth paid entitlement or change Stripe's ELITE
alias. Separate membership work is required before claiming an operational
ELITE+ account experience. FREE/PRO/ELITE account pages were additionally
captured on desktop/mobile; the ELITE_PLUS probe recorded this limitation.

## Verification

154 presentation/navigation/browser-control tests passed, plus 50 membership,
SHARK limits, Telegram preferences and authentication regression checks.
The billing-only checks require the existing OFFLINE_SAFE configuration;
they were rerun in that mode after an initial environment mismatch.

Real Chromium captures:

- 88 empty-data observations: 22 public/client/admin routes at 1440×900,
  1024×768, 390×844 and 320×740.
- 50 additional observations at desktop/mobile using an actual public cached
  sports snapshot: 340 published match records, original timestamps and
  provider values retained. Three Match Centers cover live-origin, finished
  and scheduled records. Expired live evidence is shown as pending/stale by
  the existing logic, not refreshed artificially.
- No horizontal page overflow, duplicate DOM IDs, JavaScript page errors or
  unexpected HTTP responses. The absent-match 404 is intentional. Native
  account-menu and bottom-navigation clicks, back navigation and keyboard
  traversal were exercised. Representative screenshots were visually reviewed.
- Browser traffic to external hosts was blocked. All app execution used fresh
  isolated local databases, disabled providers/payments/Telegram and no sports
  fixtures. Review accounts are explicitly local-only.

The snapshot came from the public `/api/realtime/sports` cache endpoint, which
reported `no_external_calls: true`. It is visual evidence, not certification of
provider correctness or production freshness. No publishable picks were present;
populated pick content and confirmed lineups/events require real available data.
No production backfill, reconciliation, Telegram delivery or payment ran.

## Reproduce / maintenance

`pnpm install --frozen-lockfile --ignore-scripts`, then `pnpm run build:css`.
`pnpm run check:css` rejects a stale generated bundle. Edit existing source
modules listed in `tools/build_visual_css.mjs`; do not hand-edit the bundle.

Run `python tools/run_visual_preview.py` and then
`python tools/run_visual_browser_qa.py --output <local-evidence-directory>`.
Optional `--snapshot <saved-public-cache.json>` on the preview imports only
published values into a new local database. It never fetches a provider.
The new `premium-visual` CI job verifies the bundle, semantic states and the
full empty-data browser matrix, with screenshot artifacts.
Existing release validators now check the bundle's source manifest and hash
rather than require retired individual CSS links.

The generated bundle ships in the existing release's `static/` directory;
production needs no frontend build step. Rollback is the previous commit.

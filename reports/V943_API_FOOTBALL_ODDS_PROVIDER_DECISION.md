# API-Football odds and The Odds API funding decision

**Reviewed:** 2026-10-19 19:24 Europe/Madrid  
**Scope:** static repository review and owner-provided subscription status. No provider calls, secret reads, production changes, purchases, push, or deployment.

## Decision recorded

The owner reports that API-Football and TheSportsDB are paid services and that The Odds API is currently not affordable. Treat The Odds API as **NOT FUNDED / DEFERRED** for product planning. This is an owner-provided business status, not an independent billing-dashboard verification.

NeMeSiS must not imply that The Odds API is available just because code or a key variable exists. Do not make external requests to it while unfunded. A prior production log reported the app's internal `FREE_BUDGET` deferral with zero provider calls; that is an application safety rule, not proof of The Odds API's account plan or a rejection from the provider.

## Repository findings

- The existing odds ingestion in `app.py` calls The Odds API v4 (`sports/{sport}/odds`) through `engines/odds_credentials.py`. Its configuration uses `THE_ODDS_API_KEY_*` and `ENABLE_ODDS_API`.
- The existing API-Football transport is in `engines/api_football_live_tracker_engine.py` and is reused by match/statistics features. A static source search found no API-Football `/odds` or `/odds/live` requester in the current application code.
- Existing odds persistence and consumers already exist (`odds_snapshots`, presentation/value analysis and combination flows). An API-Football adapter should feed those canonical contracts with an explicit source and timestamp; it should not create a parallel odds model or overwrite other-source snapshots.
- Example environment files are templates only. Their contents do not establish which secrets are present in Render, the purchased plan, or current provider connectivity.

## What the paid API-Football service may replace

API-Football's current public pricing page lists pre-match odds and in-play odds among its endpoints, including on the Pro plan, and states that plans differ in request volume and available seasons. Its current guide describes `/odds` for pre-match prices and `/odds/live` for in-play prices. This establishes that a second odds vendor is not automatically required; it does **not** establish the owner's exact active plan, available bookmakers, or coverage for each competition and match. Those must be verified from account/coverage evidence before promising the feature.

Official references:

- [API-Football plan and endpoint list](https://www.api-football.com/pricing)
- [API-Football guide: odds, predictions, coverage and update behavior](https://www.api-football.com/news/post/how-to-get-started-with-api-football-the-complete-beginners-guide)

## Recommended implementation path after the active release gate

1. Verify the account's current plan and check per-league/season coverage using existing dashboard evidence first; do not expose or copy API keys.
2. Add a narrow adapter on the existing API-Football transport for pre-match odds, then live odds only where coverage and a justified refresh interval support it.
3. Reuse the app's fixture IDs, canonical `odds_snapshots`, source provenance, existing freshness rules, cache, and shared API-Football request budget. Do not route these calls through The Odds API's free-profile budget.
4. Keep provider source, bookmaker, market, selection, observed-at time, and freshness attached to every displayed price. If coverage or a fresh price is missing, show a clear unavailable/stale state; never synthesize a price or derive a bookmaker quote from an AI prediction.
5. First validate with recorded fixture samples and a mocked transport. Any later real provider verification must be an explicitly budgeted natural call; do not force refreshes or spend quota during local QA.
6. Keep The Odds API documented as optional and unfunded until the owner chooses to subscribe. It may be reconsidered only if its bookmaker/market coverage adds measurable value beyond API-Football.

## Governance and validation

`NEMESIS_LIVING_ROADMAP.md` still marks `LRM-001` as the active release gate. `NEMESIS_X_IMPLEMENTATION_RULES.md` freezes Sports Core implementation until that gate is officially closed. Therefore this change records the provider decision and implementation requirements only; it does not add an endpoint or change app behavior.

Static validation performed on the current clean `main` checkout at `78f9d948`: source search confirmed the current odds requester targets The Odds API and found no API-Football odds requester. No tests were run because no application code changed. No API calls were made, so provider usage is unchanged.

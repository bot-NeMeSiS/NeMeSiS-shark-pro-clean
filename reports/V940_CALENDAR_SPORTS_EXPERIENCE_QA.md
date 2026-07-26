# V940 Calendar Sports Experience QA

## Decision

**LOCAL GATE: PASS**

Version: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`

Base commit: `c9cfd2a4cb4187eb07042e971aee3b7bad786543`

Scope: Calendar discovery experience only. Match Center, Team Center, Competition Center, Player Center, Sports Hub, SHARK and Telegram were not implemented or expanded.

Production modified: **no**

Production certified: **no**

## Product contract

The Calendar now follows the approved "Historia del dia por capas" model:

1. One request-local `sports-metrics-v1` snapshot supplies the page and `/api/calendar`.
2. Intent, date, search and filter layers remain visible, reversible and URL-shareable.
3. Day and competition indexes reduce traversal cost in long collections.
4. The compact sticky context preserves the user's current exploration layer.
5. Browser history restores the exact local scroll position without network calls.
6. Every result uses the existing canonical `match_card()` component.
7. Empty data remains an honest, actionable state.

The same contract is used by:

- `/calendar`
- `/calendario`
- `/calendario-global`
- `/partidos`
- `/partidos/calendario`
- `/api/calendar`

## Scale and data safety

- Collections tested: 5 and 500 matches.
- Direct search test: one match located from a 500-item collection.
- Populated Browser QA fixture: 42 clearly identified local QA matches.
- Real local database Browser QA: no current matches; safe empty state rendered.
- Provider calls during Calendar rendering: 0.
- Client-side external requests: 0.
- Database writes during Calendar GET: 0.
- Synthetic data presented as production data: no.

The 42-match fixture is test evidence only. It does not certify real sports data or production freshness.

## Regression protection

Sentinel contract: `V940-CALENDAR-EXPERIENCE-CONTRACT`

The contract detects:

- page/API snapshot divergence;
- direct data recalculation outside the V940 context;
- provider or write operations in the Calendar context;
- missing URL-state layers;
- missing sticky context or responsive behavior;
- non-canonical match cards;
- dead grid space for small competition groups;
- client-side network calls;
- missing local history restoration.

A mutation removing the persistent context produces `REGRESSION`, opens a P1 issue and lowers the AutoPilot score. AutoPilot can create a task and evidence package, but code changes require human approval.

Company Intelligence records the contract, cause, impact, QA result and local resolution state. It does not auto-fix code.

## Validation

- V940 focused tests: **10/10 PASS**
- Full Pytest suite: **71/71 PASS**
- V940 static gate: **PASS**
- Python compile and compileall: **PASS**
- Jinja templates: **186/186 PASS**
- Madrid Time: **PASS**
- Navigation Integrity: **PASS**
- Continuous Sentinel: **10.0/10, 0 issues**
- Imports/routes: **648 routes, 0 missing templates, 0 missing static assets**
- Route/link audit: **695 routes, 0 unsafe route smokes**
- Privacy/Secret Guard: **984 files, 0 confirmed secrets, 0 privacy findings**
- Browser QA: **PASS**
- Horizontal overflow: **0**
- Console errors: **0**
- Page errors: **0**
- Observed 5xx responses: **0**

The historical V939 checker rejects V940 because it requires the literal V939 version and cache name. This is a historical identity-check incompatibility, not a V940 regression. V939 preservation is covered by V940 runtime flags, regression tests and the current contracts.

## Not certified

- The product goal "find any match in under three seconds" needs a timed human usability study. Automated search, anchors and position restoration pass, but no human timing claim is made.
- Production data freshness, production authentication and Render runtime were not tested.
- Pixel-perfect parity is not claimed.
- Final owner visual acceptance remains pending.


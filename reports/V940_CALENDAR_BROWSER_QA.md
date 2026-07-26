# V940 Calendar Browser QA

## Result

**PASS - local and read-only**

Authoritative evidence:

- `browser_qa/V940_CALENDAR`
- `browser_qa/V940_CALENDAR_AUTHENTICATED`

Profiles:

- Desktop: `1366x768`
- Mobile: `390x844`

Scenarios:

- complete week collection;
- reversible empty search;
- direct day navigation;
- search keyboard shortcut;
- match-card navigation simulation;
- browser-back position restoration;
- active filter removal and reset.

## Real local database

The local database contained no current matches for the tested Calendar window. The Calendar rendered the premium safe empty state on desktop and mobile:

- HTTP 200;
- one Calendar root;
- one command surface;
- one persistent context;
- one collection;
- no horizontal overflow;
- no client/admin navigation mixing;
- no unsafe `None`, `null` or `undefined` copy;
- no console, page, provider or 5xx errors.

## Populated isolated fixture

A temporary database and authenticated test session rendered 42 explicitly marked QA matches across seven days and six competitions. No real provider, production database, Telegram, Stripe or OpenAI integration was used.

Results:

- canonical cards: **42/42 desktop, 42/42 mobile**;
- horizontal overflow: **0**;
- duplicate Calendar roots: **0**;
- duplicate bottom navigation: **0**;
- admin navigation in client Calendar: **0**;
- console errors: **0**;
- page errors: **0**;
- server 5xx: **0**;
- external requests: **0**;
- provider requests: **0**;
- day-anchor navigation: **PASS**;
- desktop scroll restoration: **2477 -> 2477**;
- mobile scroll restoration: **3034 -> 3034**;
- filter reset: **PASS**.

The final visual pass corrected one demonstrated issue: single-match competition groups inherited a fixed three-column grid and left excessive dead space. A scoped auto-fit rule now lets each group use its available width while keeping `match_card()` unchanged. The final screenshots were captured after that correction.

## Screenshot inventory

Eight final PNG screenshots are retained: four with the real local empty state and four with the isolated populated fixture. Their hashes can be recalculated from the two authoritative evidence directories.

The screenshots are nonblank and cover full-page desktop and mobile states. Assistant visual inspection found no overlap, clipped action, duplicated navigation or incoherent spacing in the tested views.

## Limits

- Human owner comparison and timed usability testing remain pending.
- No production or real-provider Browser QA was performed.
- The populated collection is a QA fixture, not a claim about real sports availability.
- Pixel-perfect is not claimed.


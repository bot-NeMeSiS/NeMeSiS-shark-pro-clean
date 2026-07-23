# V940 Calendar Sports Experience - Technical Specification

## 1. Authority

**Target version:** `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`  
**Approved source of truth:** `NEMESIS_SPORTS_UX_BIBLE.md`  
**Chosen product model:** Calendar alternative E, "Historia del dia por capas"  
**Base version confirmed:** `V939_AUTONOMOUS_COMPANY_INTELLIGENCE_GROWTH_AND_QUALITY_PLATFORM_FINAL`  
**Base commit inspected:** `c9cfd2a4cb4187eb07042e971aee3b7bad786543`  
**Branch inspected:** `hotfix/v937-shark-performance`  
**Initial working tree:** clean  
**Production changes allowed:** no  
**Push or deploy allowed:** no

This specification is the implementation contract for Calendar only. It does
not modify or reinterpret the approved Sports UX Bible.

## 2. Product Outcome

Calendar must stop behaving as a long list whose controls disappear. It must
become a complete chronological story in which the user can:

1. understand the selected day or intent;
2. search for a known match immediately;
3. narrow the collection with explicit, reversible layers;
4. understand how many results remain;
5. jump between days and competitions without losing global context;
6. open a match and return to the same filtered position;
7. distinguish confirmed data, empty results and provider limitations.

The commercial target is to locate a known match in under three seconds.
Implementation may make that task possible, but the target is not certified
until a timed human usability test defines the target match, start point and
success event.

## 3. Scope

### Included

- `/calendar` and its existing aliases.
- `/api/calendar`.
- Existing Calendar context builder.
- Existing Calendar template.
- Calendar-local presentation rules in the existing product stylesheet.
- One Calendar-local progressive enhancement script.
- V940 version, cache and runtime evidence.
- Calendar regression tests, static check and quality contracts.
- Browser QA at desktop and mobile sizes.

### Excluded

- Match Center.
- Team Center.
- Competition Center.
- Player Center.
- Sports Hub.
- Live redesign.
- SHARK logic or presentation.
- Telegram logic or presentation.
- Picks logic.
- New provider calls.
- New data tables or migrations.
- New analytics collection.
- Production, GitHub, push or deploy.

## 4. Canonical Data Contract

### 4.1 Single snapshot

The page and `/api/calendar` must consume the same request-local summary:

`v932_safe_dashboard_data()` -> `v940_calendar_context()` -> page/API payload.

Calendar must not:

- call a sports provider during render;
- calculate global sports metrics independently;
- query a second collection for the API response;
- replace canonical values with local filtered counts;
- mutate the database on GET.

### 4.2 Sports metrics

All global counters come from `sports-metrics-v1`:

- matches today;
- matches available;
- confirmed live;
- matches with picks;
- verified finished;
- synchronized matches.

Local collection counts are allowed only for:

- visible results;
- days represented;
- competitions represented;
- favorites in the canonical snapshot;
- incidents already present in the canonical snapshot.

Local counts must be labelled as collection context and never presented as
global sports truth.

### 4.3 Completeness and safety

The existing complete-match and false-live/stale gates remain authoritative.
Calendar does not relax them. Empty collections render an honest safe state
and never receive fabricated matches, scores, minutes, picks or counts.

## 5. URL State Contract

Calendar state is represented by safe GET parameters:

- `lane`;
- `date`;
- `q`;
- `league`;
- `team`;
- `country`;
- `status`;
- `sort`;
- `with_pick`.

Rules:

1. Every active layer is visible.
2. Every active layer can be removed independently.
3. A single reset restores the selected date/intent without hidden filters.
4. Date and lane navigation preserve compatible active layers.
5. The URL is shareable and sufficient to reconstruct the collection.
6. Unknown or unsafe values degrade to existing safe defaults.
7. No client-only filter can create a second truth.

## 6. Information Architecture

Calendar uses one collection and five ordered regions.

### Region A - Orientation

- Existing page identity.
- Existing realtime safety state.
- Existing lifecycle and decision context.
- Existing canonical KPIs.

No new sports metric is introduced.

### Region B - Calendar command surface

The first actionable region contains:

- intent lanes;
- direct match search;
- league and country filters;
- selected date navigation;
- visible-result summary;
- active-filter chips;
- clear-all action.

The surface is not duplicated elsewhere.

### Region C - Persistent compact context

A compact Calendar-only bar remains available while the collection is
explored. It contains:

- selected intent/date;
- visible result count;
- current day/competition while scrolling;
- direct return to filters.

It must not contain the full filter form and must not consume a large part of
the mobile viewport.

### Region D - Collection index

The page exposes a compact, horizontal index of the rendered days and
competitions. Every index item links to a stable in-page anchor.

The index:

- is generated from the same filtered collection;
- does not hide matches;
- uses real labels and counts;
- remains keyboard accessible;
- scrolls horizontally instead of overflowing.

### Region E - Chronological backbone

All filtered matches remain in the normal document flow:

day -> competition -> canonical `match_card()`.

No duplicate collection, carousel, virtual result or alternate card is
allowed. Each day and competition has one stable anchor and a visible heading.

## 7. Layer Model

The only layers in Phase 1 are existing, explainable inputs:

- intent/date;
- text query;
- league;
- country;
- team;
- status;
- with pick;
- favorite lane.

Layers are:

- few;
- cumulative;
- visible;
- reversible;
- represented in the URL;
- applied server-side to the canonical snapshot.

No SHARK attention score, recommendation model or implicit personalization is
introduced in this phase.

## 8. Navigation and Return Context

### 8.1 Within Calendar

- Date and lane controls preserve compatible filters.
- Day and competition anchors provide deterministic jumps.
- The persistent bar reports the section currently crossing the viewport.
- Focused navigation uses normal links, so keyboard and browser history work.

### 8.2 Calendar -> Match -> Calendar

A Calendar-local script stores only:

- the full Calendar path and query;
- the vertical position;
- the current section identifier;
- a short timestamp.

It restores position only when the browser reports a history return to the
same Calendar URL. It does not:

- store user or sports data;
- alter match links;
- intercept normal navigation;
- send analytics;
- call an API;
- write the database.

If JavaScript is unavailable, browser history and anchors remain functional.

## 9. Component Contract

### Reused without variants

- `page_header()`;
- `kpi_card()`;
- `filter_tabs()`;
- `provider_state()`;
- `empty_state()`;
- `match_card()`;
- `sports_contract_attributes()`.

### Calendar-specific structure

Calendar may add semantic wrappers and controls, but no second match-card
macro. Required markers:

- `data-v940-calendar-experience="history-layers-v1"`;
- `data-v940-calendar-command`;
- `data-v940-calendar-context`;
- `data-v940-calendar-index`;
- `data-v940-calendar-collection`;
- `data-v940-calendar-section`;
- `data-v940-calendar-filters-active`.

Every rendered match card must still carry:

- `data-v934-match-card="true"`;
- `data-v939-match-card-spec="canonical-v1"`.

## 10. Responsive Contract

### Desktop

- Search, primary facets and apply action share one readable command row.
- The compact context bar becomes sticky below the application header.
- The collection index remains one horizontal line with controlled overflow.
- Match cards keep the existing responsive grid and canonical card contract.
- No fixed side rail reduces the match grid.

### Mobile

- Search is the first filter control.
- Select controls form a stable two-column layout when width allows.
- Apply and reset actions use full available width where needed.
- The compact context bar contains one short context line and one filter
  return action.
- Intent, date and collection indexes scroll horizontally.
- No sticky layer overlaps the app header or bottom navigation.
- All interactive targets remain at least 44 px.

### Reduced motion

Scroll restoration and anchor movement are immediate when reduced motion is
requested. No decorative animation is required.

## 11. States

### Data available

Show result count, current context, index and complete chronological
collection.

### Filter returns zero

Explain that no confirmed match satisfies the active layers. Preserve the
layers, expose reset and week navigation, and do not imply provider failure.

### No canonical sports data

Use the existing provider-safe state. Keep navigation and filters available,
show zero real results and do not generate examples.

### Stale or incomplete records

Continue using existing canonical exclusion rules. They do not enter visible
counts, index anchors or cards.

### JavaScript unavailable

All GET navigation, filtering, anchors and cards remain usable. Only current
section reporting and precise history-position restoration are absent.

## 12. Performance Budget

For a collection up to 500 canonical records:

- zero provider calls during render;
- zero database writes on GET;
- one server-side filtering pass;
- one grouping pass;
- no duplicate match-card render;
- one delegated Calendar script;
- one observer for section headings, not one handler per card;
- no layout-changing image preload;
- no polling introduced by V940.

The Browser QA report must record route response time and rendered card count.
A human three-second discovery claim remains `NOT_CERTIFIED` until measured.

## 13. Accessibility

- One visible `h1` from the shared page header.
- Day and competition headings form a logical hierarchy.
- Search has an explicit accessible label.
- Active lane and filter states are programmatically exposed.
- Active filter removal has a specific accessible name.
- Collection index has a descriptive navigation label.
- Sticky context is not an assertive live region.
- Focus is visible and never trapped.
- Horizontal rails remain keyboard scrollable.
- Empty states and counts are readable without color.

## 14. Sentinel Contract

Sentinel must open a P1 product-experience issue when any of these conditions
is detected:

- Calendar page or API no longer use the canonical context builder;
- `sports-metrics-v1` is absent;
- `/api/calendar` returns a separate legacy collection;
- a match card lacks the canonical marker;
- full chronological collection marker is absent;
- active filters are hidden or cannot be reset;
- context bar or index contract is removed;
- filters conceal results without a visible result count;
- a provider call or database write is introduced in Calendar GET flow.

Static checks must be backed by mutation tests to avoid a permanently green
rule.

## 15. AutoPilot Contract

For a V940 Calendar contract regression, AutoPilot may:

- create one specific issue;
- identify route and likely files;
- attach contract evidence;
- propose acceptance tests;
- generate a Codex prompt;
- require human approval.

It may not:

- change templates, CSS or JavaScript;
- alter filters or data;
- commit, push or deploy;
- repair the regression automatically.

## 16. Company Intelligence Contract

Company Intelligence stores the V940 Calendar contract snapshot with:

- component;
- version;
- evaluated Madrid time;
- validation result;
- evidence;
- limitations;
- production certification state.

The local result must explicitly remain `production_certified: false`.

## 17. Browser QA Matrix

Minimum viewports:

- desktop `1366 x 768`;
- mobile `390 x 844`.

Minimum scenarios:

1. small confirmed collection;
2. large confirmed collection;
3. active search;
4. multiple active layers;
5. zero-result filter;
6. no-provider safe state;
7. history return after opening a match;
8. keyboard navigation;
9. reduced motion.

Validate:

- HTTP 200;
- no console or page errors;
- no horizontal page overflow;
- no duplicated navigation;
- no client/admin mixing;
- no duplicate match collection;
- no clipped text or controls;
- sticky context does not overlap shell navigation;
- all active layers are visible and removable;
- page and API share the same snapshot and visible result IDs;
- canonical cards remain unchanged.

## 18. Acceptance Criteria

V940 Calendar Phase 1 is locally accepted only when:

1. version, app version, runtime flag and service-worker cache are V940;
2. Calendar page and API share one canonical request-local context;
3. all global metrics remain `sports-metrics-v1`;
4. chronological coverage remains complete after explicit filters;
5. filters are preserved, visible, independently removable and resettable;
6. date/day/competition navigation preserves context;
7. history return restores the prior Calendar position when supported;
8. every match uses canonical `match_card()`;
9. desktop and mobile Browser QA pass;
10. mutation tests prove Sentinel detects a broken contract;
11. AutoPilot produces an approval-required task;
12. Company Intelligence records the local result without claiming
    production;
13. compile, Jinja, route smoke, navigation and relevant regression tests pass;
14. no production, provider, Telegram, Stripe, push or deploy action occurs.

## 19. Rollback

Rollback is file-scoped:

- restore the prior Calendar context function;
- restore the prior `/api/calendar` handler;
- restore the prior Calendar template and Calendar-local stylesheet rules;
- remove the Calendar-local script and V940 contract tests;
- restore V939 version, runtime flag and cache name.

No database rollback or migration is required because V940 introduces no
schema or persistent business-data change.

## 20. Known Limitation

The implementation can remove the structural causes identified in the
official video: lost filters, lost global context and linear reorientation.
It cannot honestly prove that every user finds every match in under three
seconds without a controlled usability baseline and a post-change test.

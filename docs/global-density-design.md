# Global density and hierarchy

## Shared contract

Every full HTML template loads `ui-density.css`: the base shell and the isolated
Admin client preview. `tools/audit_ui_density.py` produces the complete screen
inventory, including older operational screens. Static coverage and browser
coverage are different; the inventory does not certify every possible data state.

Desktop uses 12 px gaps, smaller headings/panel padding and compact metrics/table
rows. Collections choose columns from the available container width (310 px
minimum), with cards capped at 520 px. A single match no longer stretches across
the screen. Cards retain teams, score, schedule, state and authorized actions.
Mobile collections use one column and match actions retain 44 px touch height.
Forms, filters, membership disclosures and errors are not collapsed by this layer.

The caller-based `components/density.html` container is reused by Home, Results,
Directo, Picks, Favorites and the Admin user directory. It owns layout only:
callers still own data, forms, CSRF and authorization. Existing shared headers,
metrics, match state and empty-state components gain the same density rules.
The isolated Admin preview uses the same rules without loading user data.
Its embedded frame is now an optional native disclosure in the command center,
so activity and reliability remain closer to the operational summary. The preview
is still accessible by keyboard and with scripts disabled.

Redundant presentation variants now resolve through these shared primitives;
legacy route aliases remain compatible. Results/Calendar unification is inherited
from #159. Admin sports operations remain separate from read-only client views.
No route or permission is consolidated solely because its appearance is similar.

The targeted compatibility layer uses explicit specificity because the current
application has several legacy stylesheets. Do not append new version-specific
density overrides; adjust this contract and verify the complete cascade instead.

## Spain/Europe relevance policy

`config/audience-priority.json` defines a reviewed, explainable initial ES_EU
profile. `NEMESIS_AUDIENCE_PROFILE=GLOBAL` restores the existing catalog profile.
Other markets require a reviewed profile entry and deployment selection. Loading
is once at startup, with no DB write or external request. Invalid/missing policy
falls back atomically to the catalog policy and emits a non-sensitive warning.

Canonical identities and country scopes remain authoritative. Policies adjust
competition ranks, retaining catalog tiers and weights; unknown competitions
remain unknown. Lifecycle lanes precede competition rank; within those lanes,
competition rank precedes per-match bonuses. Existing filters remain available.
The policy never modifies provider collection, pick selection, odds or settlement.
Operational callers retain the legacy registry by default. Only display enrichment
opts into the audience registry; provider window selection and legacy operational
league ranking are tested to keep their original ranks.

Evidence reviewed on 2026-10-03:

- [CSD official sports habits survey](https://www.csd.gob.es/es/encuesta-de-habitos-deportivos-en-espana).
  Research framework for Spanish sport consumption. Participation figures are
  not treated as football league audience shares.
- [UEFA European football landscape, 25 September 2026](https://www.uefa.com/news-media/news/02a9-21aca98834ff-f54c73c29132-1000--the-key-trends-at-the-heart-of-european-club-football/).
  Evidence of European interest across domestic, continental and national-team
  football; not a survey of our Spanish customers.

**The exact ordering is an editorial market hypothesis, not measured customer
preference.** Neither source proves that a specific Spanish customer prefers
LaLiga to the Premier League. No fabricated audience percentages or engagement
scores are stored. Each rule states this limitation and its rationale.

Before changing the profile based on product behavior, study consented aggregate
competition impressions, detail opens and favorite additions by market, normalized
for available fixtures and exposure. Compare multiple weeks and tournament periods;
retain sample sizes and uncertainty and guard against exposure feedback loops.
This PR does not introduce tracking or collect new personal data.

## Verification

`test_global_density_browser.py` covers 19 screen families at 390/1440 px and
populated shared match collections at 320/390/768/1440/1920 px. It checks document
overflow, bounded card widths, multiple records per desktop row, genuine zero-zero
score display and mobile action size. Fixtures are synthetic and offline.
Existing journey-control and competition identity/lifecycle regressions remain
part of validation. This does not imply all optional Admin data states have been
exercised. Production visual review remains separate from local fixture evidence.

DB_PATH, providers, cron, payments, users, memberships and picks are outside the
implementation scope; layout does not change their writes or permissions.

Local validation: 50 new browser cases passed, 135 existing/new regression cases
passed, and after isolating the audience policy from operational ranking, 88
identity/calendar/provider/Telegram/policy cases passed. All 197 Jinja templates
parse. The Windows temporary-directory permission issue during the first run was
resolved by using dedicated temporary directories in this workspace.

## Unified-base validation

This revision is validated after the canonical sports entity navigation layer entered the PR chain. Density and ES/EU presentation priority remain presentation-only and must not replace Sports Core identity, lifecycle, historical memory, provider, pick or settlement truth.

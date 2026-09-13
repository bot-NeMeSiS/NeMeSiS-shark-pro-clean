# I18N Coverage Matrix

CX-DESIGN-02-R5 / LOCAL_ONLY / IN_PROGRESS. No production certification.
This matrix measures coverage, not merely catalogue completeness.

## Canonical Contract

- One explicit UI catalogue: localization/ui.json. ES is the default and fallback.
- Languages: es, en, fr. Spanish source messages are never technical translation keys.
- Saved authenticated preference, then session/cookie, Accept-Language, then ES.
- The existing client_profiles.preferences_json stores language without replacing other preferences.
- Cookie: HttpOnly, SameSite=Lax, one year; Secure on HTTPS. Existing CSRF required.
- Logout clears authentication, not the language cookie. One PWA, unchanged brand metadata.
- Sports timezone always Europe/Madrid. Locale changes text/date format, never the instant.
- French greeting: Bonjour 05:00-11:59; Bon apres-midi 12:00-19:59; Bonsoir otherwise.
- Team/player/provider names and official competition data are not translated automatically.
- Missing UI translation falls back to Spanish and is a coverage gap, not PASS.

## Coverage

| Area | Connected | Remaining | Status |
|---|---|---|---|
| CLIENT_CRITICAL | Navigation, Home, Calendar, Live, cards, Picks; Match Center factual and typed context, form/H2H, score states | Advanced SHARK explanations, expanded filters and data-quality details | PARTIAL |
| CLIENT_SECONDARY | Team/Player/Competition literals and quality states, Team context, round/season evidence, Telegram, Madrid Track Record instants, Favorites/Activity/Alerts/Preferences forms and feedback | Populated secondary branches, provider event/position code maps, remaining knowledge narratives | PARTIAL |
| AUTH | Login/register/reset, real validation and expired-token messages; selector; CSRF remains active | Public landing, exhaustive global error branches | PARTIAL |
| ACCOUNT | Language persistence, account actions, recent activity labels/dates, linked preferences and four safe local preference actions | Exhaustive security/error branches | PARTIAL |
| MEMBERSHIPS | Plan descriptions, benefits, controls, empty checkout state and configured monthly cadence | Legal checkout acknowledgements and commercial paths not exercised | PARTIAL |
| SHARK | Dedicated page literals, known states, typed pressure/recent-change signals, app-owned entity pressure text | Free-form explanations and deeper knowledge evidence; do not invent translations of external narratives | PARTIAL |
| SUPPORT | Form, categories, help, persisted receipt, rate/validation/storage errors ES/EN/FR; real local admin inbox | Production rollout, notifications and human response not verified | PASS_LOCAL / PRODUCTION_NOT_TESTED |
| ADMIN | Shared translated components only | Operational copy and module-specific coverage | BACKLOG |
| SYSTEM_COPY | Locale metadata and basic feedback | Global flash/API errors and deeper system states | BACKLOG |

CLIENT_CRITICAL_ES_EN_FR = NOT_COMPLETE. Zero missing entries inside the current
catalogue does not mean zero untranslated product text. No blanket translation of
rendered HTML, provider fields, IDs or user messages is allowed.
R5 catalogue: 1020 entries (R4: 775). Explicit ownership: APP_OWNED_TEXT is localized;
PROVIDER_PROPER_NOUN preserved; PROVIDER_DYNAMIC_TEXT and USER_CONTENT stay verbatim.
The absence of technical keys in captured pages does not certify all hidden branches.

R5 closes reported Resultado disponible and Conocimiento ampliado copy, bounded
round/market/risk/freshness patterns and common secondary-page copy. Final selected
captures contain no exact untranslated catalogue lines in EN/FR, but this is a
bounded detector, not complete translation certification. Known remaining fields
include provider event/position codes (Normal Goal, MED), free-form narratives,
legal/commercial and populated secondary/error branches. Admin remains backlog.
Do not claim VISIBLE_UNLOCALIZED_CLIENT_TEXT = 0 globally.
R5 browser matrix: 216 deduplicated observations, 28 screen IDs; 96 Madrid cases
across Tokyo/New York/London/Paris and ES/EN/FR. Product data and language are separate.

## Design Memory

- Home compact match content uses a bounded 44px team row on mobile.
- A single desktop Home match uses a horizontal row; the footer owns one full
  grid column. French labels must not wrap letter by letter inside a narrow track.
- Calendar repeats neither the group competition visually nor a confidence panel
  in each row; canonical metadata and the adjacent Madrid time remain present.
- Account mobile services use one column, with native Activity/Security disclosures.
  Desktop initializes them open; the user's later choice is not reset on resize.
- Native disclosure QA waits for the requested state and records actual tap events.
- Home empty pick content is unframed; do not reintroduce a nested empty-state card.
- The mobile KPI labels wrap at word boundaries, not inside English/French words.
- Calendar grouping uses the Madrid date and time ordering uses the absolute instant,
  including the repeated autumn hour. Existing state priority remains unchanged.
- Unknown foreign timezone / ambiguous provider civil time: pending, not a guessed Madrid time.
- Existing manual/admin Madrid civil values retain their established interpretation.
- Translation cannot certify shark anatomy or conformance to the 16 target images.
- Match overview uses three desktop columns and one mobile column; available modules
  follow in two desktop columns. No fake confidence, recommendation or external narrative.
- Support success means a committed inbox row, never an email or a staff reply.
- Upcoming match's primary value is its existing Madrid clock; known score wins,
  including real 0-0. Missing/stale updates clear the previous score, never invent 0-0.
- League logo payload is sanitized at the caller and rendered through the same
  crest load/error exclusivity; missing logo is neutral initials, not an official mark.
- Calendar date navigation owns one mobile row; French Aujourd'hui cannot split
  within a word at 360px. Desktop controls and secondary filters have separate rows.
- Status chips retain at least min-content width and wrap between words; do not
  shrink official operational state labels letter by letter to hide layout defects.
- Ocean raster is a continuous background layer with constrained contrast, not a
  separate wallpaper card. Admin atmosphere remains subdued. Anatomy is not certified.

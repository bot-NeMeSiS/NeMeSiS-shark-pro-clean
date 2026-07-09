# V925 Reference Model Audit

## Base and scope

- Local base: `V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL`.
- Preserved route recovery: V923 client and sports-route guards.
- References reviewed: 16 real images from `reference_images/` and `reference_manifest.json`.
- Evidence gate: Browser QA project artifacts still contain no valid screenshots; no pixel-perfect claim is allowed.

## Reference inventory

| Category | Images | Main target |
| --- | ---: | --- |
| Admin | 7 | Dashboard and operational command centers |
| Calendar | 1 | Match calendar and filters |
| Client | 1 | Mobile-first client dashboard |
| Live | 1 | Live/upcoming/finished sports board |
| Memberships | 1 | Plan comparison and safe checkout state |
| Picks | 1 | Premium picks and market context |
| Profile | 1 | Account, plan and activity state |
| SHARK | 1 | Safe assistant mode and capabilities |
| Telegram | 1 | Delivery quality and configuration state |
| Track record | 1 | Results/evidence presentation |

## Shared visual model

- Dark neutral application shell with cyan/blue actions and green, amber and magenta status accents.
- Compact first viewport: navigation, title, KPIs and next action appear without a large empty lead-in.
- Dense cards with clear labels, strong numeric hierarchy and restrained radius.
- Repeated structures use grids or compact rows; operational tables favor scanning over decoration.
- Mobile navigation is persistent and route-oriented. Desktop navigation separates public, client and admin contexts.
- Admin is a command center: current state, alerts, queues and actions are visible together.
- Sports screens expose provider/cache state and never replace missing data with invented matches, odds or results.

## Internal design brief

- **Hierarchy:** title, current state, next action, operational detail.
- **Density:** 8-14 px internal gaps, compact cards, no decorative empty bands.
- **Cards:** maximum 8 px radius in the V925 layer, visible border, one responsibility per card.
- **KPIs:** short label, real value or explicit safe state, supporting context.
- **Tabs and filters:** horizontal, compact and scroll-safe on mobile.
- **Empty states:** explain what is missing, why it is safe and what can be done next.
- **CTAs:** direct route actions; no API endpoints as page links.
- **Admin:** separate shell, no client bottom navigation and no floating client SHARK.
- **Mobile:** stable five-item navigation, one-column content and no body overflow.

## Screen targets

The V925 pass covers public home, client app, calendar, live, picks, SHARK, Telegram, profile, memberships, admin dashboard, Workforce, Sentinel, issues, Codex outbox and Telegram command center.

The 18 visual queue items remain `BLOCKED_NO_SCREENSHOT` until a valid `screenshot_path` is imported. Static and manual visual improvements do not mark those items visually resolved.

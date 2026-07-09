# V925 Final Rendered Home Duplicate Hero QA

## Release identity

- Local version: `V925_REFERENCE_MODEL_FULL_APP_REBUILD_QUALITY_PASS_FINAL`.
- `VERSION.txt`, `APP_VERSION` and local runtime match.
- Local deployment alignment: `aligned_local_files`.
- Production before this QA started: `V924_GLOBAL_UI_EMPTY_SPACE_CLIENT_VALUE_SPORTS_DATA_ODDS_FIX_FINAL`.
- Production changed externally during QA to `V925_REFERENCE_MODEL_FULL_APP_REBUILD_QUALITY_PASS_FINAL`, aligned and with zero active Sentinel issues.

## Rendered home result

`tools/check_v925_rendered_home_no_duplicate_hero.py` renders a real `GET /` with the Flask test client and parses the returned HTML.

- HTTP status: 200.
- Rendered H1 count: 1.
- H1: `NeMeSiS SHARK PRO`.
- V925 public hero count: 1.
- Legacy hero classes rendered: none.
- Legacy hero copy rendered: none.
- First structural child of the V925 public page: `.v925-public-hero.v925-above-fold`.
- Required sections present: Hoy en NeMeSiS, Qué hace la app, Planes and Confianza.
- Duplicate hero: no.

## Template diagnosis and correction

The duplicate reported in V924 production is not reproducible in the local V925 rendered HTML. Its historical candidate was the second legacy public block in `templates/home.html` (the old V783/public product hero). V925 had already replaced it with one integrated public experience.

The real Render home was checked after that external V925 deployment: HTTP 200, one H1, one exact `.v925-public-hero`, no legacy second title and no legacy copies. That deployed page did not yet contain the final visible `Confianza` heading, which identifies it as an earlier V925 package rather than the final package certified here.

This final pass added two narrow safeguards:

1. A visible `Confianza` heading in the existing V925 trust band; no new product block was created.
2. A rendered-DOM check that fails on two H1 elements, more than one V925 hero, the old `NeMeSiS SHARK PRO app deportiva premium` title, both legacy copies, legacy hero classes or a structural wrapper before the V925 hero.

Files adjusted in this final pass:

- `templates/home.html`
- `static/app.css`
- `tools/check_v925_rendered_home_no_duplicate_hero.py`
- `app.py`: optional historical outbox reads in `/api/runtime-version` now fail closed when the clean deploy package does not include that runtime artifact.

## V923 client hotfix preservation

| Route | Result |
| --- | ---: |
| `/cliente-login` | 200 |
| `/login` | 200 |
| `/registro` | 200 |
| `/app` | 302 safe login redirect |
| `/calendar` | 200 |
| `/calendario` | 200 |
| `/live` | 200 |
| `/directo` | 200 |
| `/picks` | 200 |
| `/shark` | 200 |
| `/telegram` | 302 safe login redirect |
| `/profile` | 302 safe login redirect |
| `/support` | 200 |

`check_v923_client_routes_internal_error_recovery.py` passed.

## Admin and sports contracts

- `/admin/dashboard`, `/admin/automation-workforce` and `/admin/autonomous-company-sentinel` return protected redirects and never 500.
- Admin templates contain the V925 command-center marker.
- `Salir cliente`, `Capturas0` and `Comparaciones18` are absent from the checked admin templates.
- The scoped compact admin shell CSS is present; client bottom navigation and floating SHARK remain excluded from admin.
- Calendar, live, picks and SHARK render real-data or explicit safe-state language with no mandatory external refresh.
- The extracted deploy root can render `/api/runtime-version` without requiring a local Codex outbox file.
- No match, team, score, minute, pick, market, odds, ROI or result was invented.

## Validation matrix

Passed:

- `python -m py_compile app.py`
- `python -m compileall app.py engines tools automation_workforce`
- Madrid Time self-test
- V923 client route recovery check
- V925 reference-model check
- V925 rendered-home duplicate-hero check
- Continuous Sentinel static: score 10.0, zero issues
- Release identity check; service-worker cache V925
- Deploy-root identity check
- Imports/routes verification: 600 routes, zero missing templates/static files
- All-routes link audit: 633 routes, zero unsafe smoke failures

## Final package contract

The final build must include this report and the rendered-home check. ZIP and deploy root are accepted only with:

- `forbidden_count=0`
- `missing_required_root=[]`
- no nested parent folder
- no local database, logs, internal ZIP, `.git`, `.venv` or real secret

No push or Render deployment was performed by this QA pass. Render now reports V925, but the final ZIP from this report should be deployed/redeployed and verified by both runtime identity and rendered-home checks because an earlier package used the same V925 version label.

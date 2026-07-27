# V940 Routes Links And Aliases Audit

- version: `V940_NEMESIS_SPORTS_EXPERIENCE_PHASE_1_FOUNDATION_FINAL`
- generated_at: `2026-07-27T00:41:06`
- routes_registered: `707`
- templates_scanned: `188`
- direct_api_hrefs: `21`
- empty_hash_links: `0`
- javascript_void_links: `0`
- forms_without_method_or_safe_action: `0`
- unsafe_smoke_count: `0`

## Smoke
- `/` -> `200` safe=`true`
- `/cliente-login` -> `200` safe=`true`
- `/registro` -> `200` safe=`true`
- `/app` -> `302` safe=`true`
- `/calendar` -> `200` safe=`true`
- `/calendario` -> `200` safe=`true`
- `/live` -> `200` safe=`true`
- `/directo` -> `200` safe=`true`
- `/picks` -> `200` safe=`true`
- `/shark` -> `200` safe=`true`
- `/telegram` -> `302` safe=`true`
- `/profile` -> `302` safe=`true`
- `/support` -> `200` safe=`true`
- `/track-record` -> `200` safe=`true`
- `/admin-login` -> `200` safe=`true`
- `/admin/dashboard` -> `302` safe=`true`
- `/admin/autonomous-company-sentinel` -> `302` safe=`true`
- `/admin/sentinel-issues` -> `302` safe=`true`
- `/admin/sentinel-codex-outbox` -> `302` safe=`true`
- `/admin/not-found-events` -> `302` safe=`true`
- `/admin/telegram/command-center` -> `302` safe=`true`
- `/api/runtime-version` -> `200` safe=`true`
- `/ruta-inventada-v910` -> `404` safe=`true`
- `/api/ruta-inventada-v910` -> `404` safe=`true`
- `/manifest.json` -> `200` safe=`true`
- `/service-worker.js` -> `200` safe=`true`

## Notes
- Admin protected routes are expected to redirect or deny without session.
- API 404 is expected to return safe JSON.
- HTML 404 is expected to render the premium not-found template.
- Direct admin/automation API hrefs should be replaced with buttons/fetch in future UI passes if any remain.

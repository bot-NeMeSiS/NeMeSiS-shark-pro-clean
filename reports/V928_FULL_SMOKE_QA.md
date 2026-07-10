# V928 Full Smoke QA

- Version: `V928_CANONICAL_REFERENCE_FULL_APP_ADMIN_CLIENT_MOBILE_REBUILD_FINAL`.
- Resultado: `OK`.
- DB: temporal y vacia; la ruta local no se publica.
- Telegram enviado: no.
- Pagos ejecutados: no.

| Sesion/metodo | Ruta | Estado | OK |
|---|---|---:|---|
| public GET | `/` | 200 | True |
| public GET | `/cliente-login` | 200 | True |
| public GET | `/login` | 200 | True |
| public GET | `/registro` | 200 | True |
| public GET | `/support` | 200 | True |
| public GET | `/manifest.json` | 200 | True |
| public GET | `/service-worker.js` | 200 | True |
| public GET | `/api/runtime-version` | 200 | True |
| anonymous-protected GET | `/app` | 302 | True |
| anonymous-protected GET | `/profile` | 302 | True |
| anonymous-protected GET | `/admin/dashboard` | 302 | True |
| anonymous-protected GET | `/admin/automation-workforce` | 302 | True |
| anonymous-admin-api GET | `/api/admin/automation-workforce/status` | 403 | True |
| client GET | `/app` | 200 | True |
| client GET | `/calendar` | 200 | True |
| client GET | `/calendario` | 200 | True |
| client GET | `/live` | 200 | True |
| client GET | `/directo` | 200 | True |
| client GET | `/picks` | 200 | True |
| client GET | `/track-record` | 200 | True |
| client GET | `/shark` | 200 | True |
| client GET | `/telegram` | 200 | True |
| client GET | `/profile` | 200 | True |
| client GET | `/memberships` | 200 | True |
| admin GET | `/admin-login` | 302 | True |
| admin GET | `/admin/dashboard` | 200 | True |
| admin GET | `/admin/telegram/command-center` | 200 | True |
| admin GET | `/admin/users` | 200 | True |
| admin GET | `/admin/payments` | 200 | True |
| admin GET | `/admin/picks` | 200 | True |
| admin GET | `/admin/data-center` | 200 | True |
| admin GET | `/admin/automation-workforce` | 200 | True |
| admin GET | `/admin/autonomous-company-sentinel` | 200 | True |
| admin GET | `/admin/sentinel-issues` | 200 | True |
| admin GET | `/admin/sentinel-codex-outbox` | 200 | True |
| admin GET | `/admin/launch-certification` | 200 | True |
| invalid-form POST | `/cliente-login` | 403 | True |
| invalid-form POST | `/login` | 403 | True |
| invalid-form POST | `/registro` | 403 | True |
| 404-html GET | `/ruta-inventada-v928` | 404 | True |
| 404-api GET | `/api/ruta-inventada-v928` | 404 | True |
| controlled-500 GET | `/__v928_controlled_500` | 500 | True |

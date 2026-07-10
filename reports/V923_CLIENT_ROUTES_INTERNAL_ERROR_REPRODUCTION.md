# V923 Client Routes Internal Error Reproduction

version: V923_CLIENT_ROUTES_INTERNAL_ERROR_RECOVERY_AFTER_V922_FINAL
generated_at_madrid: 2026-07-10T09:22:29+02:00
client_routes_recovered: true

| route | status | redirect | ok | exception | probable_cause | fix_applied |
|---|---:|---|---|---|---|---|
| `/` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/cliente-login` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/login` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/registro` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/app` | 302 | `/cliente-login?next=/app` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/calendar` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/calendario` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/live` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/directo` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/picks` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/shark` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/telegram` | 302 | `/cliente-login?next=/telegram` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/profile` | 302 | `/cliente-login` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/support` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/api/runtime-version` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/ruta-inventada` | 404 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/api/ruta-inventada` | 404 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/manifest.json` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |
| `/service-worker.js` | 200 | `` | True | `` | not_reproduced_local | route_health_guard_and_safe_500_registration |

## POST invalidos

- `/cliente-login` status=403 ok=True
- `/login` status=403 ok=True
- `/registro` status=403 ok=True

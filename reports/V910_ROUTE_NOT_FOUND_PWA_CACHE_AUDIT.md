# V910 Route Not Found PWA Cache Audit

- version: `V910_FULL_PROJECT_HIDDEN_AUDIT_ROUTE_NOT_FOUND_BROWSER_QA_READY_FINAL`
- service_worker_cache: `NEMESIS_CACHE_V910`
- manifest_start_url: `/`
- manifest_scope: `/`
- html_404: premium template with sanitized path
- api_404: safe JSON
- legacy_aliases: `/dashboard`, `/client`, `/cliente`, `/admin-panel`, `/directos`, `/recomendaciones`, `/soporte`, `/perfil`, `/mi-cuenta`

## Safe behavior
- Navigation 404 is not cached by the service worker.
- PWA starts at `/`.
- API unknown routes return JSON 404.
- Common old routes redirect through safe aliases where configured.

## Human action
If a user still sees an old Not Found screen after deploy, clear browser/PWA storage or reinstall the PWA to drop old service worker cache.

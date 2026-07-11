# V934 Admin Reference QA

## Updated surfaces

- `/admin/dashboard`: compact realtime operations summary.
- `/admin/data-center`: provider, cache, sync and freshness diagnostics.
- `/admin/realtime-center`: new command-center view for safe sports operations.
- Admin navigation: direct `Tiempo real` entry within the existing admin shell.

## Operational controls

- Local cache refresh invalidates only the in-process V934 sports cache.
- Dry-run sync never contacts a provider and never writes the database.
- Health check is read-only.
- All admin APIs remain protected; unauthenticated status access returned 403.

Admin and client navigation remain separated. No secret values, real sends, payments or destructive database actions are exposed.

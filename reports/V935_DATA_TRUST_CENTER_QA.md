# V935 Data Trust Center QA

Rutas:

- `/admin/data-trust-center`
- `/admin/data-quality`

APIs protegidas:

- `GET /api/admin/data-trust/summary`
- `GET /api/admin/data-trust/issues`
- `POST /api/admin/data-trust/run-safe-validation`
- `POST /api/admin/data-trust/refresh-cache`

Sin sesion, la pagina redirige al login y las APIs devuelven 403. Con sesion admin mock segura, pagina y validacion CSRF responden 200. El panel separa lifecycle de partidos, picks publicables/evaluables, frescura, issues deduplicados, proveedor y ultima sync. Las acciones son dry-run/cache local: no llaman proveedor ni escriben DB.

Estado local: `WAITING_FOR_REAL_DATA`, sin blockers falsos y sin afirmar que hay datos inexistentes.

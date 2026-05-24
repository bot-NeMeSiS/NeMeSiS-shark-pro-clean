# NeMeSiS SHARK PRO V522

PORTABLE CLEAN BUILD + REAL DATA FEED ACTIVATION

## Objetivo

V522 deja el paquete final mas portable para Render y activa un feed real controlado por admin usando TheSportsDB Premium.

## Incluye

- ZIP final con rutas Unix/Linux dentro del archivo.
- Build limpio sin READMEs antiguos, bases locales, logs, zips ni cache Python.
- Feed SportsDB para importar partidos reales a SQLite.
- Ruta admin `/admin/sportsdb-feed`.
- API protegida `/api/sportsdb/sync-feed`.
- Diagnosticos ampliados con partidos cacheados, ultimo feed sync y estado de admin.
- Bootstrap admin seguro con variables Render o `/admin-bootstrap` solo si no existe ningun ADMIN.

## Variables Render

- `DB_PATH=/data/database.db`
- `THESPORTSDB_API_KEY`
- `THESPORTSDB_KEY`
- `ENABLE_LIVE_API=true`
- `ADMIN_EMAIL`
- `ADMIN_USERNAME`
- `ADMIN_PASSWORD`
- `ADMIN_NAME`

## Legalidad

No usa scraping. Solo API permitida, datos propios/importados autorizados y cache SQLite.

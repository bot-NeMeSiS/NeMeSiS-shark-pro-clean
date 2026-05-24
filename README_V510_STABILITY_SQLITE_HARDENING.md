# NeMeSiS SHARK PRO V510 — Stability & SQLite Hardening

Versión preparada sobre V509 para corregir el bloqueo visto en Render:

```txt
sqlite3.OperationalError: database is locked
```

## Cambios principales

- `database_manager.py` centralizado.
- SQLite con `timeout=30`.
- `PRAGMA busy_timeout=30000`.
- `PRAGMA journal_mode=WAL`.
- `PRAGMA synchronous=NORMAL`.
- Retry corto ante `database is locked`.
- `seed_core()` protegido con lock interno.
- Marcador persistente `core_seed_version` para evitar seed repetido en cada lectura.
- Se mantiene `DB_PATH=/data/database.db`.
- Se mantiene arquitectura V509 con engines separados.
- Añadido `/service-worker.js` mínimo para evitar 404 por PWA/cache previa.

## Mantiene

- Real Time Match Engine.
- Match Hub 2.0.
- Favorites Intelligence.
- Telegram Auto Engine V2.
- SHARK AI Sports Context.
- Engines separados:
  - cache_engine
  - crest_engine
  - live_engine
  - match_engine
  - shark_engine
  - telegram_engine

## Verificado

- `app.py` compila OK.
- `database_manager.py` compila OK.
- Rutas principales probadas con Flask test client:
  - `/`
  - `/match-hub`
  - `/live`
  - `/picks`
  - `/perfil`
  - `/favorites`
  - `/api/health`
  - `/api/diagnostics`

## Render

Variables recomendadas:

```txt
DB_PATH=/data/database.db
```

No incluye base de datos local, logs, `.git`, `__pycache__` ni ZIPs antiguos.

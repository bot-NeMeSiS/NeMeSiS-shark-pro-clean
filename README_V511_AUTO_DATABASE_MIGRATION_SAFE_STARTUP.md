# NeMeSiS SHARK PRO — V511 AUTO DATABASE MIGRATION SAFE STARTUP

Versión preparada sobre V510 para corregir el fallo real detectado en Render:

```txt
sqlite3.OperationalError: table matches has no column named match_date
```

## Qué corrige

Render conserva `/data/database.db` entre despliegues. Si una versión anterior creó tablas antiguas, `CREATE TABLE IF NOT EXISTS` no añade columnas nuevas. V511 añade una capa de migración segura para que la app pueda arrancar con una DB persistente antigua sin borrarla manualmente.

## Incluye

- Migración automática de columnas faltantes.
- Protección para `matches.match_date`.
- Protección para columnas V509/V510 en `matches`, `teams`, `competitions`, `favorites` y `picks`.
- Registro de migración en `schema_migrations`.
- Registro de versión en `automation_state`.
- Mantiene SQLite hardening V510:
  - WAL mode.
  - timeout.
  - busy timeout.
  - retry ante bloqueos.
- Mantiene V509 completa:
  - Real Time Match Engine.
  - Match Hub 2.0.
  - Favorites Intelligence.
  - Telegram Auto Engine V2.
  - SHARK AI Sports Context.
  - engines separados.
- Mantiene `DB_PATH=/data/database.db`.

## Importante

Ya no debería hacer falta borrar manualmente `/data/database.db` para este cambio de schema.

## Verificación local

- `python3 -m py_compile app.py` OK.
- ZIP limpio sin `.git`, `__pycache__`, logs ni DB local.

## Deploy

Subir a GitHub y dejar que Render redeploye.

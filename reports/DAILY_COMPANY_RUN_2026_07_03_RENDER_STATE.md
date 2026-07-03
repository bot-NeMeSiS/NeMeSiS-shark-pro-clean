# DAILY COMPANY RUN 2026-07-03 - RENDER STATE

Endpoint consultado:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

## Produccion Render

- Version Render real: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`
- Version local: `V885_CLIENT_SIDEBAR_RESTORE_BEST_POSITION_NAV_FINAL`
- Estado: **BLOQUEADOR CRITICO**
- Motivo: produccion no esta desplegando el codigo local reciente.

## Runtime real observado

- `db_path`: `/data/database.db`
- `app_py_path`: `/opt/render/project/src/app.py`
- Telegram configurado: true
- The Odds configurado: true
- API-SPORTS configurado: true
- API-Football configurado: true
- OpenAI configurado: false
- `team_logo_cache_count`: 0
- `league_logo_cache_count`: 0
- Usage guard: activo, cache-first, no page render calls.
- `last_error`: `Invalid header value ...`
- `last_sync`: `2026-06-26T22:53:25Z`

## Diagnostico

Render esta operativo, pero sirve V855. No se puede certificar visualmente V885 en produccion hasta que se suba el contenido correcto a GitHub y se haga deploy manual con cache limpio.

## Accion requerida

1. Subir contenido descomprimido del ZIP V885 a la raiz real del repo.
2. Confirmar `VERSION.txt` y `app.py` en GitHub con V885.
3. Render: Manual Deploy -> Clear build cache & deploy.
4. Reconsultar `/api/runtime-version` hasta ver V885.

# V884 Render Codex Deploy Awareness QA

## Render real

Endpoint revisado: https://bot-apuestas-crgf.onrender.com/api/runtime-version

Resultado observado:

- app_version: V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL
- version_txt: V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL
- app_py_path: /opt/render/project/src/app.py
- db_path: /data/database.db
- openai_configured: false
- telegram_configured: true
- api_sports_configured: true
- api_football_configured: true
- the_odds_configured: true
- team_logo_cache_count: 0
- league_logo_cache_count: 0
- last_error: Invalid header value historico visible en runtime V855

## Diagnostico

Produccion no sirve V884. Sigue pendiente alinear GitHub/Render y hacer deploy manual con clear build cache.

## Accion exacta

Subir el contenido descomprimido del ZIP V884 a la raiz correcta del repo, confirmar VERSION.txt/app.py en GitHub y ejecutar Manual Deploy con Clear build cache en Render.

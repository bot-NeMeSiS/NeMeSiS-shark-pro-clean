# V875 Real Render V874 Deployment Alignment QA

## Runtime real consultado

URL: `https://bot-apuestas-crgf.onrender.com/api/runtime-version`

## Resultado

- HTTP: `200`.
- `app_version`: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.
- `version`: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.
- `version_txt`: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.
- `db_path`: `/data/database.db`.
- `app_py_path`: `/opt/render/project/src/app.py`.
- `static_app_css_hash`: `163b2a20d9d1af94`.
- `static_app_css_size`: `794668`.
- `last_error`: `Invalid header value b'386760cfa00b37f98d680113043f9768\n'`.
- `openai_configured`: `false`.
- `team_logo_cache_count`: `0`.
- `league_logo_cache_count`: `0`.
- `telegram_configured`: `true`.
- `the_odds_configured`: `true`.
- `api_sports_configured`: `true`.
- `api_football_configured`: `true`.
- `automation_secret_configured`: `true`.
- `usage_guard.no_page_render_calls`: `true`.

## Blocker

Producción no está en V874. Está en V855. Por tanto:

- No se puede certificar visual V874 en Render.
- No se puede certificar corrección V873/V874 de header en producción.
- No se puede certificar CSS/cache V874 en producción.
- Cualquier revisión visual real de producción corresponde a V855, no a V874/V875.

## Instrucciones exactas para deploy manual

1. Subir a GitHub el árbol local oficial con V875.
2. Verificar que Render apunta al repo/branch correcto.
3. Confirmar start command y root del servicio: `/opt/render/project/src`.
4. Deploy manual en Render.
5. Reabrir `/api/runtime-version`.
6. Validar que `app_version` y `version_txt` sean `V875_REAL_RENDER_V874_PRODUCTION_VISUAL_AND_OPERATIONS_CERTIFICATION_FINAL`.
7. Validar `static_app_css_hash` distinto al hash V855 si cambió CSS/base.
8. Confirmar que `last_error` ya no expone bytes crudos.


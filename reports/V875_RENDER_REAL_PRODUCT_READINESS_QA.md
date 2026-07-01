# V875 Render Real Product Readiness QA

## Estado

Render real fue consultado en `/api/runtime-version` antes de declarar readiness de producto.

## Resultado Render

- Version real en produccion: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.
- Version local objetivo: `V875_REAL_PRODUCT_READINESS_RENDER_VISUAL_REVENUE_FINAL`.
- Estado: `BLOCKER_DEPLOY_MISMATCH`.
- Conclusion: no se puede certificar V874/V875 visual ni operativamente en produccion hasta desplegar el ZIP correcto.

## Runtime real observado

- `last_error`: `Invalid header value ...` sigue apareciendo en Render real.
- `openai_configured`: `false`.
- `team_logo_cache_count`: `0`.
- `league_logo_cache_count`: `0`.
- `telegram_configured`: `true`.
- `the_odds_configured`: `true`.
- `api_sports_configured`: `true`.
- `api_football_configured`: `true`.
- `automation_secret_configured`: `true`.
- `db_path`: `/data/database.db`.
- `usage_guard.no_page_render_calls`: `true`.

## Accion exacta

1. Subir a Render el ZIP final V875 o alinear el repo/branch usado por Render.
2. Confirmar que el start command apunta al root correcto.
3. Volver a consultar `/api/runtime-version`.
4. Solo si devuelve V875, ejecutar certificacion visual real.


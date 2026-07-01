# V876 Render Version Alignment Diagnosis

## Diagnostico ejecutivo

La produccion Render consultada en `/api/runtime-version` no esta alineada con el paquete local. Localmente se parte de V875 y se crea V876 como paquete de alineacion; Render real sigue sirviendo una version antigua observada como `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL` en esta ejecucion.

Nota: el usuario reporto que Render seguia en V871. La consulta realizada durante V876 devolvio V855. En ambos casos el diagnostico operativo es el mismo: Render no esta sirviendo V875/V876.

## Local

- `VERSION.txt` antes de V876: `V875_REAL_PRODUCT_READINESS_RENDER_VISUAL_REVENUE_FINAL`.
- `APP_VERSION` antes de V876: `V875_REAL_PRODUCT_READINESS_RENDER_VISUAL_REVENUE_FINAL`.
- `VERSION.txt` V876: `V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL`.
- `APP_VERSION` V876: `V876_RENDER_VERSION_ALIGNMENT_AND_FINAL_VISUAL_DEPLOY_CHECK_FINAL`.
- ZIP V875 inspeccionado: contiene `app.py` y `VERSION.txt` en raiz.
- ZIP V875 inspeccionado: no contiene carpeta anidada del proyecto.
- ZIP V875 inspeccionado: no contiene ZIPs internos ni DB local.
- `render.yaml`: start command `gunicorn app:app --bind 0.0.0.0:$PORT --workers 1 --threads 3 --worker-class gthread --timeout 90`.
- `Procfile`: `web: gunicorn app:app`.

## Render real

- `app_version`: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.
- `version`: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.
- `version_txt`: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`.
- `app_py_path`: `/opt/render/project/src/app.py`.
- `current_working_directory`: `/opt/render/project/src`.
- `db_path`: `/data/database.db`.
- `static_app_css_hash`: `163b2a20d9d1af94`.
- `static_app_css_mtime`: `2026-06-27T09:29:35+02:00`.
- `last_error`: `Invalid header value ...`.
- `openai_configured`: `false`.
- `team_logo_cache_count`: `0`.
- `league_logo_cache_count`: `0`.
- `telegram_configured`: `true`.
- `the_odds_configured`: `true`.
- `api_sports_configured`: `true`.
- `api_football_configured`: `true`.
- `automation_secret_configured`: `true`.

## Causa mas probable

Render esta usando un commit/rama/root anterior o no se ha ejecutado un deploy manual del contenido local V875/V876. El ZIP local correcto por si solo no actualiza Render.

## Accion requerida

1. Subir el contenido descomprimido del ZIP V876 a la raiz del repositorio correcto.
2. Confirmar en GitHub que `VERSION.txt` y `app.py` en raiz muestran V876.
3. En Render, ejecutar `Clear build cache & deploy`.
4. Confirmar que `/api/runtime-version` devuelve V876.


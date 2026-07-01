# V879 Render V878 Runtime QA

## Producción real

Endpoint revisado:

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

Resultado observado:

- `app_version`: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`
- `version_txt`: `V855_FULL_ECOSYSTEM_REFERENCE_REBUILD_CLIENT_ADMIN_MEMBERSHIPS_FINAL`
- `app_py_path`: `/opt/render/project/src/app.py`
- `current_working_directory`: `/opt/render/project/src`
- `static_app_css_hash`: `163b2a20d9d1af94`
- `static_app_css_size`: `794668`
- `last_error`: `Invalid header value b'386760cfa00b37f98d680113043f9768\n'`
- `openai_configured`: `false`
- `team_logo_cache_count`: `0`
- `league_logo_cache_count`: `0`
- `telegram_configured`: `true`
- `the_odds_configured`: `true`
- `api_sports_configured`: `true`
- `api_football_configured`: `true`
- `automation_secret_configured`: `true`

## Diagnóstico

Render no está sirviendo V878 ni V879. La certificación visual real de V878 queda bloqueada hasta desplegar el ZIP actual en la raíz correcta del repositorio y ejecutar un deploy limpio.

## Acción exacta

1. Subir el contenido del ZIP V879 descomprimido a la raíz del repositorio.
2. Confirmar en GitHub que `VERSION.txt` y `app.py` muestran V879.
3. En Render ejecutar `Clear build cache & deploy`.
4. Volver a consultar `/api/runtime-version`.
5. Solo si devuelve V879, hacer browser QA y capturas reales.

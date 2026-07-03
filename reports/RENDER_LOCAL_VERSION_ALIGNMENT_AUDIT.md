# Render Local Version Alignment Audit

## Endpoint Render consultado

`https://bot-apuestas-crgf.onrender.com/api/runtime-version`

## Version local

```text
V886_REAL_BROWSER_NAV_VISUAL_QA_AFTER_V885_FINAL
```

## Version Render real

```text
V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL
```

## Comparacion

Estado: **NO ALINEADO**

Render no esta desplegando la version local V886.

## Datos Render relevantes

```text
app_py_path: /opt/render/project/src/app.py
current_working_directory: /opt/render/project/src
db_path: /data/database.db
static_app_css_hash: a7107f484eaa3dcd
static_app_css_size: 899598
last_error: Invalid header value detectado en runtime; valor saneado para diagnostico seguro.
last_error_state.active: false
openai_configured: false
telegram_configured: true
the_odds_configured: true
api_sports_configured: true
api_football_configured: true
team_logo_cache_count: 0
league_logo_cache_count: 0
```

## Flags Render

Render expone flags hasta `has_v883_visual_company_worker=true` y tambien flags posteriores preservados en runtime, pero el `app_version/version/version_txt` activo es V883. Eso significa que el codigo desplegado no corresponde a la version local actual V886.

## Diferencia CSS

```text
Local static_app_css_hash:  d9c4779f30c8b98e
Render static_app_css_hash: a7107f484eaa3dcd
```

Resultado: CSS de Render no coincide con CSS local.

## Veredicto

Render esta sirviendo una version antigua respecto al proyecto local. No se puede afirmar que V885/V886 esten en produccion hasta que `/api/runtime-version` devuelva V886 y el hash CSS coincida o cambie a una build esperada posterior.

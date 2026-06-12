# V728 FINAL CLIENT EXPERIENCE MADRID TIME LIVE POLISH

## Resumen ejecutivo

Versión preparada sobre la base limpia V727. Esta iteración se centra en dos problemas reales detectados por el usuario:

1. Algunas pantallas seguían pudiendo mostrar horarios crudos o campos fallback (`kickoff_time`, `match_time`) en vez de la hora española normalizada.
2. La experiencia visual de cliente necesitaba más compactación, orden y consistencia en Live, Calendar, Sports Hub, Match Detail, Picks y Combis.

La versión resultante es:

`V728_FINAL_CLIENT_EXPERIENCE_MADRID_TIME_LIVE_POLISH`

## Cambios principales

### 1. Horarios Madrid blindados en plantillas

Se añadieron filtros Jinja centralizados:

- `match_time_short`
- `match_time_label`
- `match_date_label`

Estos filtros fuerzan a que las plantillas pasen por `engines/madrid_time_engine.py` antes de mostrar horas al cliente.

Pantallas reforzadas:

- Home
- Dashboard / Client Overview
- Sports Hub
- Live
- Calendar
- Picks
- Combis
- Favoritos
- Match Detail
- Match Hub
- Team Detail
- Smart Dashboard
- Unified Intelligence Hub
- Daily Briefing
- SHARK Core
- Algunas vistas admin relacionadas con partidos

### 2. Motor Madrid enriquecido

`engines/madrid_time_engine.py` ahora expone campos de display más explícitos:

- `display_time`
- `display_date_label`
- `display_status_label`
- `kickoff_display`

Se mantiene el uso correcto de:

`zoneinfo.ZoneInfo("Europe/Madrid")`

Sin offsets fijos `+1` o `+2`.

Casos obligatorios:

- `2026-06-12T19:00:00Z -> 21:00 Madrid`
- `2026-12-12T20:00:00Z -> 21:00 Madrid`

### 3. Live / Calendar / Sports Hub más compactos

Se añadió un bloque CSS V728 para:

- reducir espacios muertos
- mejorar densidad en móvil
- reforzar tarjetas de partido
- mejorar legibilidad de hora, marcador y equipos
- diferenciar estados En directo / Próximo / Finalizado
- suavizar diseño premium sin saturación
- evitar tarjetas enormes en móvil
- mejorar bottom nav y SHARK flotante

### 4. Auditoría visual/horaria estática

Nuevo script:

`tools/check_v728_client_experience.py`

Genera:

- `V728_VISUAL_TIME_QA_REPORT.md`
- `reports/V728_VISUAL_TIME_QA_REPORT.json`

Comprueba que las pantallas cliente críticas usan filtros Madrid y no presentan patrones de hora cruda en plantillas principales.

### 5. Release workflow

Se actualizó `tools/build_clean_release.py` para incluir informes/manifests V728 y mantener ZIP limpio.

También se corrigió el título dinámico de `tools/audit_release_zip.py` para que no quede fijado en V723.

### 6. Telegram Reliability script más robusto

`tools/check_telegram_reliability.py` ahora no revienta de forma confusa si faltan dependencias locales como Flask. Genera un informe claro `DEPENDENCY_MISSING` sin enviar mensajes ni exponer secrets.

## Archivos modificados

- `app.py`
- `VERSION.txt`
- `engines/madrid_time_engine.py`
- `templates/calendar.html`
- `templates/live.html`
- `templates/sports_hub.html`
- `templates/combis.html`
- `templates/favorites.html`
- `templates/home.html`
- `templates/client_overview.html`
- `templates/daily_briefing.html`
- `templates/match_detail.html`
- `templates/match_hub.html`
- `templates/smart_dashboard.html`
- `templates/unified_intelligence_hub.html`
- `templates/team_detail.html`
- `templates/shark_core.html`
- `templates/data_depth.html`
- `templates/discovery.html`
- `templates/opportunities.html`
- `templates/picks.html`
- `templates/autonomous_ecosystem.html`
- `templates/betting_recommendations.html`
- `templates/admin_betting_center.html`
- `templates/admin_intelligence_engine.html`
- `templates/admin_sports_data_picks.html`
- `static/app.css`
- `tools/build_clean_release.py`
- `tools/audit_release_zip.py`
- `tools/check_telegram_reliability.py`
- `tools/check_v728_client_experience.py`

## Validación ejecutada en este entorno

- `python -m py_compile app.py`: OK
- `python -m py_compile engines/madrid_time_engine.py`: OK
- `python -m py_compile tools/check_v728_client_experience.py`: OK
- `python -m compileall -q app.py engines services blueprints tools tests`: OK
- `python tools/check_madrid_times.py`: OK
- `python tools/check_v728_client_experience.py`: OK
- `python tools/check_telegram_reliability.py`: genera informe claro `DEPENDENCY_MISSING` porque este entorno no tiene Flask instalado.

Limitación del entorno:

- `tools/smoke_check.py`, `tools/validate_release.py` y `pytest` no pueden completarse aquí porque este sandbox no tiene Flask/Jinja instalados, aunque `requirements.txt` sí los incluye.

## Qué queda pendiente en Render

Tras desplegar V728, comprobar:

- `/api/runtime-version` debe mostrar V728.
- Un partido conocido a las 21:00 España debe mostrarse como 21:00 en Calendar, Sports Hub, Picks, Combis y Match Detail.
- `/admin/time-diagnostics` debe confirmar Europe/Madrid.
- `/admin/telegram/command-center` debe explicar el estado real de Telegram con variables de Render.

## Veredicto

V728 queda preparada como release Render Ready orientada a experiencia final de cliente, horarios Madrid más blindados y visual compacto. La certificación definitiva depende de desplegar en Render y probar con DB/Telegram reales.

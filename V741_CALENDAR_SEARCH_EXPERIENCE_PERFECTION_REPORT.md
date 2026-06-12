# V741 Calendar Search Experience Perfection

## Estado

Versión preparada sobre V740: `V741_CALENDAR_SEARCH_EXPERIENCE_PERFECTION`.

## Objetivo

Convertir la pantalla de partidos en un calendario premium completo, fácil de buscar y ordenado para cliente, manteniendo intactos Telegram, Cron, pagos, membresías, DB_PATH, Madrid Time, picks y visual V736/V737/V740.

## Cambios principales

- `Partidos` pasa a comportarse como calendario central con `/calendar`, `/calendario`, `/calendario-global`, `/partidos` y `/partidos/calendario`.
- Nuevo sistema `calendar_experience_data()` para construir la experiencia de calendario desde datos reales ya sincronizados.
- Filtros cliente por día, semana, directo, favoritos, picks, España, Andalucía y próximos 21 días.
- Buscador por texto libre: equipo, liga, país, estado o competición.
- Filtros adicionales por liga, equipo, país/zona y orden.
- Orden por importancia SHARK, hora, liga o picks primero.
- Agrupación clara por fecha y competición.
- Escudos/fallbacks protegidos en cada tarjeta de partido.
- Ligas y competiciones pasan por castellano con `competition_es`.
- API `/api/calendar` devuelve la misma estructura enriquecida que la pantalla.
- Nuevo centro admin `/admin/calendar-experience` y `/admin/calendar-qa`.
- Nueva validación `tools/check_v741_calendar_experience.py`.
- CSS V741 anti-solape y mobile-safe para nombres largos, ligas, botones, tarjetas y scroll horizontal.

## Seguridad

- No llama APIs externas desde el calendario.
- No inventa partidos ni resultados.
- No muestra cuotas o picks si no existen.
- No toca secrets.
- No modifica `DB_PATH=/data/database.db`.
- No cambia Telegram, Cron, Stripe ni membresías.

## Validación local realizada

- `python -m py_compile app.py`: OK
- `python -m compileall -q .`: OK
- `python tools/check_madrid_times.py`: OK
- Checks V728–V741: OK
- Parseo Jinja de templates: OK
- `python tools/build_clean_release.py`: OK
- `python tools/audit_release_zip.py`: OK

## Pendiente real de producción

Tras desplegar en Render, validar con datos reales:

- `/api/runtime-version`
- `/calendar`
- `/partidos`
- `/api/calendar?lane=week`
- `/admin/calendar-experience`
- `/admin/final-release`
- `/admin/production-readiness`

Si la pantalla aparece vacía en producción, la causa ya no será el calendario, sino falta de sincronización de datos reales en la base persistente.

# V801_CALENDAR_MATCHES_REFERENCE_FLOW_REAL_DATA_PERFECTION

Base: V800_REFERENCE_SCREEN_APP_FIDELITY_REAL_DATA_NAVIGATION_FINAL.

## Revisión de vídeos y objetivo

Se revisaron los vídeos subidos del estado actual de la app cliente. El mayor punto detectado fue la pantalla de Partidos: visualmente ya tenía una base oscura premium, pero necesitaba funcionar como calendario central real, con días, ligas importantes, búsqueda y enlaces de detalle/SHARK más claros. También se detectó un riesgo real: la plantilla estaba esperando `day_groups`, mientras el backend devolvía `groups`; eso podía provocar estados vacíos aunque hubiera partidos filtrados.

## Cambios principales

- `/partidos`, `/calendar`, `/calendario` y `/partidos/calendario` quedan como una única pantalla de calendario real.
- Corregida compatibilidad backend/frontend: ahora el contexto devuelve `groups` y `day_groups`.
- Añadido selector horizontal de días: Hoy, Mañana y próximos 7 días con conteo real desde SQLite.
- Añadidos filtros rápidos: Hoy, Mañana, Semana, Directo, Con pick, Top mundial, España, UEFA, Selecciones, Resultados, Favoritos y 21 días.
- Añadido buscador real por equipo/liga/país/competición.
- Añadidos selectores de liga, país y orden: importancia, hora, liga o picks primero.
- Añadido rail de ligas importantes usando `IMPORTANT_COMPETITIONS`, sin gastar créditos extra y filtrando lo que ya está sincronizado.
- Reforzado el flujo de enlaces: partido → detalle real; partido → SHARK por ancla; directo/pick desde calendario → detalle.
- Rediseño CSS V801 para acercarse más a las referencias: cards más compactas, agrupación día/liga, filas de partido más tipo marcador, panel lateral de estado real y responsive móvil.

## Datos reales protegidos

- No se inventan partidos.
- No se inventan cuotas.
- No se inventan resultados.
- No se inventan picks.
- Si no hay datos, se muestra estado vacío: sin calendario real, esperando sincronización o cambia de filtro.

## No tocado

- DB_PATH.
- AUTOMATION_SECRET.
- Telegram real.
- Render Cron.
- Usuarios, sesiones, membresías, pagos, Stripe y lógica de picks.
- Madrid Time.

## Validación local

- `python -m py_compile app.py` OK.
- `python -m compileall -q app.py engines tools` OK.
- 144 plantillas Jinja parseadas OK.
- `python tools/check_madrid_times.py` OK.
- `python tools/check_v801_calendar_matches_flow.py` OK.
- Flask smoke no ejecutado en sandbox porque Flask no está instalado.
- Telegram real no enviado desde sandbox.

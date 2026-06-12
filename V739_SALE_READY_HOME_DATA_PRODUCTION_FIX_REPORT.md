# V739 — Sale Ready Home Data Production Fix

## Objetivo
Corregir el problema visto en producción donde el panel **Hoy en NeMeSiS** mostraba siempre `0` en partidos, directo, picks y favoritos.

## Causa detectada
La ruta `/` estaba usando `home_light_data()` con datos estáticos para responder rápido en Render:

- `upcoming: 0`
- `live: 0`
- `picks: []`
- `favorites: []`

Eso hacía que el panel de inicio enseñara ceros aunque la base de datos real pudiera tener partidos o picks.

## Solución aplicada
Se añadió `home_live_summary_data()`:

- consulta SQLite real de forma ligera;
- no llama APIs externas;
- no inventa datos;
- no rompe si la DB aún no tiene tablas/datos;
- cuenta partidos, directo, picks publicados y favoritos reales;
- muestra próximos partidos reales en el home;
- si producción aún no ha sincronizado datos, muestra estado pendiente en vez de vender un cero falso.

## Resultado visual
El panel del home ahora funciona así:

- si hay datos reales: muestra cifras reales;
- si no hay datos: muestra `—` y el mensaje de sincronización pendiente;
- nunca vuelve a usar los ceros hardcodeados de la landing.

## Qué significa “validación real en producción”
Significa comprobar la app en el Render real, con las variables reales y la DB persistente real:

- `/api/runtime-version` devuelve V739;
- `/api/health` responde OK;
- `DB_PATH=/data/database.db` está usando disco persistente;
- Cron con secret responde 200 y sin secret 403;
- Telegram Command Center ve token/chat/candidatos reales;
- The Odds API/SportsDB cargan partidos reales;
- el home ya muestra cifras reales o pendiente de sincronización, no ceros falsos;
- no hay errores 500/502 en rutas críticas.

## Alcance seguro
No se toca Telegram, Cron, Stripe, membresías, DB_PATH, picks/cuotas ni Madrid Time. Es una corrección de datos de home y cierre final de release candidate.

## Validaciones realizadas en sandbox
- py_compile app.py: OK
- compileall: OK
- check_madrid_times: OK
- checks V728–V739: OK
- build_clean_release: OK
- audit_release_zip: OK

## Limitación honesta
El sandbox no tiene secrets reales de Render, Telegram, The Odds API ni Stripe. Por eso la validación comercial final debe hacerse en Render tras desplegar.

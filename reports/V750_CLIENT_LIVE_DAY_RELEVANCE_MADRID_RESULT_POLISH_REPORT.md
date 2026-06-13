# V750_CLIENT_LIVE_DAY_RELEVANCE_MADRID_RESULT_POLISH

## Objetivo

Pulir la pantalla cliente `/live` / `/directo` para que siga el estilo premium de NeMeSiS SHARK PRO y no parezca una pantalla alterada/legacy: días claros, hora Madrid, marcador/resultado, relevancia de partido y organización por competición.

## Cambios realizados

- Rediseñada `templates/live.html` con una vista premium por días y ligas.
- Reforzado `engines/live_experience_engine.py`:
  - enriquecimiento de cada partido para live,
  - grupos por día,
  - ligas ordenadas por relevancia,
  - directo primero,
  - picks/favoritos destacados,
  - score/status sin inventar marcador,
  - hora Madrid como display principal.
- Añadido CSS V750 en `static/app.css`:
  - cards premium responsive,
  - scorebox claro,
  - estado live/finished/upcoming,
  - mobile-safe.
- Añadido `tools/check_v750_client_live_experience.py` para validar estructura de live.
- Actualizado `VERSION.txt`.
- Actualizado builder para incluir reportes/manifest V750.

## Reglas conservadas

- No se toca Telegram/Cron V749B.
- No se toca DB_PATH.
- No se inventan resultados.
- No se hacen llamadas externas.
- Los enlaces siguen llevando a `/match/<id>`.
- Las horas siguen pasando por helpers Madrid.

## Resultado esperado

El usuario verá `/live` y `/directo` como un centro premium:

- Hero SHARK claro.
- Filtros visibles.
- Búsqueda simple.
- Partidos agrupados por día.
- Dentro de cada día, ligas relevantes primero.
- En directo primero, luego próximos/finalizados.
- Marcador/resultado claro.
- Estado y hora Madrid claros.
- Picks/favoritos destacados.

## Validación local

Pendiente de resultado final en el ZIP: `compileall`, check V750, checks de seguridad/Madrid/V749B y auditoría ZIP.

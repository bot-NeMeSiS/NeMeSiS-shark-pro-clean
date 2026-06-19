# V821 Render Production Hotfix Report

Version: `V821_PRODUCTION_502_CRESTS_RUNTIME_HOTFIX`

## Prioridad

Eliminar 502/timeouts tras V820 sin romper:

- V818 master tick;
- V819 dedup visual;
- V820 visual y escudos reales;
- Telegram/Cron;
- DB_PATH;
- Madrid Time;
- pagos y membresias.

## Cambios aplicados

- Version activa V821.
- Shell conserva V820 y añade marcador V821.
- Cache busting CSS actualizado a V821.
- `crest_engine` endurecido con helpers seguros.
- Rutas de logos ligeras y no bloqueantes.
- Render de partidos sin escrituras a cache de logos.
- Runtime version ampliado con indicadores del hotfix.

## Riesgo eliminado

Un conjunto de imagenes de una pagina ya no puede disparar inicializacion pesada, migraciones o escrituras SQLite repetidas.

## Estado

Render Ready tras validaciones y ZIP auditado.

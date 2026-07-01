# V882 Match Data End To End Audit

## Configuración

- API-SPORTS/API-Football: preservado con guard.
- The Odds API: preservado con guard.
- `no_page_render_calls`: preservado por diseño, no se fuerzan llamadas externas desde render.
- Madrid Time: preservado.
- Secretos: no expuestos.

## DB/Cache

Con DB temporal de QA:

- Endpoints `/api/live`, `/api/match-hub`, `/api/picks`, `/api/picks/stats` responden 200.
- Picks publicados visibles: 0.
- Las rutas cliente `/partidos`, `/calendar`, `/live`, `/directo`, `/picks` responden 200 y contienen estados seguros.

Con entorno local heredando `DB_PATH=/data/database.db`:

- Windows no puede abrir `/data`, lo que genera 500 en endpoints de datos.
- No se modifica `DB_PATH`; se documenta como diferencia local/Render.

## Filtros y templates

- Calendario usa `match_hub`, `calendar_experience_data` y grupos por día/liga.
- Live usa caché/API tracker y fallback a tablas locales.
- Picks usa `published_picks_for_user` y no inventa cuota/selección.

## Diagnóstico

Si existen partidos en DB/cache, las pantallas siguen mostrándolos.
Si no existen, V882 mejora el estado visible para que el cliente entienda que falta proveedor, sync, caché o que los filtros han eliminado resultados.

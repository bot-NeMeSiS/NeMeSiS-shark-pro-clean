# MATCH DEDUPLICATION REPORT

Fecha: 2026-06-10  
Proyecto: NeMeSiS SHARK PRO  
Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`

## 1. Problema real

El usuario podia ver el mismo partido repetido en distintas vistas porque la deduplicacion existente dependia principalmente del `id` tecnico.

Cuando el mismo partido llegaba desde fuentes distintas, por ejemplo:

- TheSportsDB
- The Odds API
- importacion manual/autorizada
- cache local

cada fuente podia generar un `id` diferente. Aunque el partido fuera el mismo, la app lo trataba como eventos distintos.

## 2. Causa raiz exacta

La causa raiz estaba en la funcion `dedupe_matches_list()`.

Antes:

- Usaba `id` como clave principal.
- Solo usaba una clave alternativa si no habia `id`.
- Por tanto, dos registros con ids distintos no se deduplicaban aunque tuvieran mismo partido, misma competicion y mismo kickoff.

Tambien habia otro punto debil en `match_hub()`:

- El merge de `today_matches + window_matches + results` usaba `seen` por `id`.
- Si el mismo partido venia con dos ids, entraban dos tarjetas.

## 3. Clave logica implementada

Se implemento una clave unica logica:

`competition | home_team | away_team | kickoff`

Ejemplo:

`laliga | barcelona | real madrid | 2026-06-10T21:00`

Con esta regla, un partido aparece una sola vez aunque tenga ids distintos por fuente.

## 4. Correcciones aplicadas

Archivo modificado:

- `app.py`

Funciones nuevas o reforzadas:

- `match_logical_key(match)`
- `match_quality_score(match)`
- `merge_match_payload(primary, duplicate)`
- `dedupe_matches_list(matches)`
- `match_deduplication_metrics(sample_limit=5000)`
- `cleanup_duplicate_matches(cur=None)`

Funciones conectadas al dedupe:

- `get_matches()`
- `get_upcoming_matches()`
- `get_results_matches()`
- `match_hub()`
- `sports_hub_groups()`
- `annotate_sports_hub_matches()`
- `favorite_feed()`
- `favorite_feed_full()`
- `import_matches()`
- `upsert_sportsdb_matches()`
- `match_calendar_diagnostics()`

Tambien se blindo:

- `current_user_id()` para que no rompa fuera de request context durante tareas de fondo.
- `sync_log_start()` para evitar colisiones de `api_sync_logs.id` en ejecuciones muy seguidas y cerrar conexion siempre.

## 5. Limpieza de base de datos

Despues de sincronizaciones/importaciones se ejecuta limpieza segura:

- Detecta grupos duplicados por clave logica.
- Conserva el registro de mayor calidad.
- Fusiona campos utiles del duplicado hacia el conservado si faltan.
- Actualiza `picks.match_id` hacia el id conservado.
- Actualiza `live_matches.match_id` hacia el id conservado.
- Elimina los duplicados de `matches`.
- Limpia cache de `match-hub`.

No borra datos utiles sin fusionarlos primero.

## 6. Metricas admin añadidas

`match_calendar_diagnostics()` ahora devuelve:

- `total_matches`
- `unique_matches`
- `duplicates_detected`
- `duplicate_groups`
- `duplicate_examples`

Estas metricas quedan disponibles en:

- `/api/matches/diagnostics`
- Data Center y resumenes que usan `match_calendar_diagnostics()`

## 7. Pruebas realizadas

Las pruebas se hicieron en SQLite temporal para no tocar produccion.

### Prueba 1: duplicado directo

Datos:

- Barcelona vs Real Madrid
- LaLiga
- 2026-06-10 21:00
- Dos ids distintos
- Dos fuentes distintas

Resultado:

- Antes: `total_matches=3`
- Unicos: `unique_matches=2`
- Duplicados detectados: `1`
- Duplicados eliminados: `1`
- Despues: `total_matches=2`
- Duplicados restantes: `0`
- Vista visible: `2` partidos, no `3`

### Prueba 2: importacion repetida

Se importo dos veces el mismo lote con duplicados.

Resultado:

- Primera importacion: `duplicates_removed=1`, `duplicate_groups=1`
- Segunda importacion: `duplicates_removed=1`, `duplicate_groups=1`
- Diagnostico final: `total_matches=2`, `unique_matches=2`, `duplicates_detected=0`

### Prueba 3: scheduler varias veces

Se ejecuto el scheduler dos veces en base temporal.

Resultado:

- No genero duplicados.
- Los errores devueltos fueron esperados por falta de claves externas en entorno local temporal:
  - falta `THESPORTSDB_API_KEY`
  - falta `THE_ODDS_API_KEY`
  - falta destino Telegram

No hubo duplicacion de partidos.

### Prueba 4: daily automation varias veces

Se ejecuto la automatizacion diaria dos veces con backup simulado.

Resultado:

- No genero duplicados.
- La automatizacion quedo marcada como no OK por dependencias externas no configuradas en la base temporal, no por dedupe.

### Prueba 5: Live duplicado

Datos:

- PSG vs Bayern
- Champions League
- 2026-06-10 20:00
- Dos ids distintos
- Estado live

Resultado:

- `get_matches(..., "live")`: `1`
- `match_hub(..., "live")`: `1`
- Limpieza DB: `duplicates_removed=1`
- Duplicados despues: `0`

### Prueba 6: rutas principales

Con base temporal duplicada, respondieron 200:

- `/`
- `/sports-hub`
- `/today`
- `/live`
- `/calendar`
- `/match-hub`
- `/favorites`
- `/picks`
- `/recomendaciones`
- `/shark`
- `/api/matches/diagnostics`
- `/api/calendar?date=2026-06-10`
- `/api/live?date=2026-06-10`
- `/api/match-hub?date=2026-06-10`

## 8. Compileall

Resultado:

- `app.py`: OK
- `engines`: OK
- `database_manager.py`: OK
- `services`: OK

## 9. Limitacion honesta

En esta carpeta local no hay copia real de la base persistente de Render `/data/database.db`.

Por tanto, no se puede listar el numero real de duplicados existentes ahora mismo en produccion desde este entorno. Lo que si queda reparado es:

- la causa raiz del duplicado por ids distintos
- la capa de presentacion
- la limpieza tras sync/import
- las metricas admin para detectar duplicados reales en Render

## 10. Estado final

Criterio conseguido en codigo:

Un partido, una fila, una tarjeta.

La app ya no depende del `id` tecnico para evitar duplicados visibles. Usa una clave deportiva real:

`competicion + local + visitante + kickoff`.


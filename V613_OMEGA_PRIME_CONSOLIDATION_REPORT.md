# V613 OMEGA PRIME CONSOLIDATION REPORT

## Resumen ejecutivo
NeMeSiS SHARK PRO queda consolidado sobre la base V612 sin rehacer la app ni retirar funcionalidades. La prioridad de esta pasada ha sido rendimiento, trazabilidad y estabilidad Render: rutas ligeras, consultas menos repetidas, cache TTL corto, indices SQLite seguros y observabilidad de latencia.

## Clasificacion de hallazgos

### CRITICO
- La causa critica historica de pantalla negra ya estaba corregida en V612: `rows()` y `execute()` no llaman a `seed_core()` ni a `init_db()`.
- En Omega se verifico de nuevo que `/`, `/api/health`, `/api/startup-check` y `/api/runtime-version` no disparan dashboard pesado.

### ALTO
- `dashboard_data()` recalculaba muchos bloques en una sola peticion: partidos, proximos, picks, combis, favoritos, hub, resultados, candidatos, rendimiento, live flow, diagnosticos y data center.
- `get_matches()` y `get_upcoming_matches()` resolvian identidad/escudo de equipos repetidamente dentro de cada listado.
- `get_picks()` podia recalcular ajustes SHARK Learning y lecturas de picks varias veces por la misma vista.

### MEDIO
- Faltaban indices especificos para consultas frecuentes por fecha/prioridad/hora, picks publicados, usuarios por rol/membresia, favoritos recientes y expiracion de cache persistente.
- Los endpoints de runtime no mostraban estado de cache de alivio.

### BAJO
- El arbol raiz conserva muchos informes, parches y ZIPs historicos. No se borran del workspace para no perder historial, pero el ZIP final limpio los excluye.

## Cambios implementados
- Version actualizada a `V613_OMEGA_PRIME_CONSOLIDATION`.
- Cache TTL en memoria con copia defensiva y limite simple de tamano.
- Cache corto aplicado a:
  - `get_matches()` 30s
  - `get_upcoming_matches()` 45s
  - `get_picks()` 20s
  - `competitions()` 60s
  - `dashboard_data()` 12s por usuario/membresia/rol
- `get_matches()` y `get_upcoming_matches()` ahora reutilizan identidades de equipo dentro de la misma consulta, reduciendo N+1 repetidos sobre equipos.
- Cabecera `X-Response-Time-ms` en respuestas.
- Log `[RENDER] slow_request` para rutas que superen 3000 ms.
- `/api/startup-check` y `/api/runtime-version` exponen `memory_cache`.
- Nuevos indices SQLite seguros:
  - `idx_matches_date_priority_time`
  - `idx_matches_date_league_time`
  - `idx_picks_status_published`
  - `idx_users_role_membership`
  - `idx_favorites_user_created`
  - `idx_persistent_cache_expires`

## Metricas de rendimiento esperadas
No se pudo ejecutar Flask test client local porque el runtime local no tiene Flask instalado y la red del sandbox bloquea instalar dependencias. La validacion de rendimiento se basa en reduccion de trabajo real:

| Ruta/Bloque | Antes | Despues |
|---|---|---|
| Home `/` | Ligera desde V612 | Sigue ligera, sin dashboard pesado |
| Dashboard | Recalculo completo por peticion | Cache por usuario 12s |
| Picks | Query + normalizacion en cada llamada | Cache 20s por filtro/membresia |
| Live/Calendario | Identidad de equipo repetida por fila | Identidad reutilizada + cache listado |
| Competiciones | Query repetida en varios bloques | Cache 60s |

Objetivos de Render reforzados:
- Home: <2s en condiciones normales.
- Login: <1s salvo inicializacion DB/migracion primera vez.
- Picks: <3s con cache caliente.
- Live: <3s con cache caliente.

## Trazabilidad modulo/ruta/engine/template
| Modulo | Estado | Ruta | Engine | Template | API | Conectado |
|---|---|---|---|---|---|---|
| SHARK | Activo | `/shark` | `shark_engine`, `shark_intelligence_core` | `shark.html` | `/api/shark` | Si |
| Telegram | Activo | `/telegram`, `/admin/telegram` | `telegram_delivery_engine`, `telegram_engine` | `telegram.html`, `admin_telegram.html` | `/api/telegram/*` | Si |
| Live | Activo | `/live`, `/live-depth` | `live_engine`, `match_engine` | `live.html`, `live_depth.html` | `/api/live/*` | Si |
| Picks | Activo | `/picks`, `/admin/picks` | `picks_engine`, `pick_grading_engine` | `picks.html`, `admin_picks.html` | `/api/picks` | Si |
| Calendario | Activo | `/calendar`, `/match-hub` | `match_engine`, `match_sync_engine` | `match_hub.html` | `/api/matches/*` | Si |
| Warehouse | Activo | `/admin/data-center` | `historical_warehouse_engine`, `football_data_warehouse_engine` | `admin_data_center.html` | `/api/warehouse/*` | Si |
| Learning | Activo | `/admin/data-center` | `shark_learning_engine` | `admin_data_center.html` | `/api/shark-learning/*` | Si |
| Membresias | Activo | `/membresias`, `/admin/memberships` | `membership_engine` | `membership.html`, `admin_memberships.html` | `/api/admin/membership-summary` | Si |
| Observabilidad | Activo | `/admin/observability` | `observability_engine` | `admin_observability.html` | `/api/observability/summary` | Si |

## Seguridad y Render
- `render.yaml` usa `gunicorn app:app --workers 1 --threads 3 --worker-class gthread --timeout 90`.
- `DB_PATH=/data/database.db` conservado.
- `database_manager.py` mantiene WAL, busy timeout, timeout y foreign keys.
- CSRF, rate limit, cabeceras y acceso admin permanecen activos.

## Validacion ejecutada
- `python -m compileall app.py engines database_manager.py`: OK.
- Inspeccion AST:
  - `rows()` sin `seed_core()` ni `init_db()`: OK.
  - `execute()` sin `seed_core()` ni `init_db()`: OK.
  - `home()` sin `dashboard_data()`: OK.
  - `health()` sin dashboard ni rows: OK.
  - rutas criticas registradas: OK.
- Flask test client: no ejecutado localmente por falta de Flask en runtime local; `requirements.txt` si lo incluye para Render.

## Riesgos restantes
- `app.py` sigue siendo grande y acumula muchas generaciones historicas. Riesgo medio para mantenimiento, aunque funcional.
- Hay muchos informes y parches historicos en raiz. Riesgo bajo para Render si el ZIP limpio se usa, pero conviene moverlos a `/docs/archive` en una fase futura.
- La primera peticion que active migraciones en una DB antigua puede tardar mas de lo habitual, aunque ya no se dispara desde `/` ni health.

## Hoja de ruta V614-V616
- V614: extraer rutas admin/clientes a blueprints sin cambiar UX.
- V615: smoke tests reales con dependencias instaladas y fixture SQLite minima.
- V616: archivado documental y reduccion progresiva de `app.py` manteniendo compatibilidad.

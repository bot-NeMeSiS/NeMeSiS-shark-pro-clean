# V721 DATA MEMORY HISTORIC SHARK

## Versión
`V721_DATA_MEMORY_HISTORIC_SHARK`

## Objetivo
Añadir memoria deportiva persistente para que NeMeSiS SHARK PRO empiece a guardar histórico útil de sincronizaciones, partidos, picks, descartes y Telegram, preparando el camino para estadísticas reales, ROI, control de calidad y futuro machine learning.

## Cambios principales

### 1. Nuevo motor de memoria
Añadido:

- `engines/data_memory_engine.py`

Funciones principales:

- `ensure_data_memory_schema`
- `record_api_sync_run`
- `remember_match_snapshot`
- `remember_pick_decision`
- `remember_pick_discard`
- `remember_telegram_delivery`
- `remember_team_identity`
- `data_memory_summary`
- `cleanup_old_memory`
- `safe_memory_call`

### 2. Nuevas tablas SQLite
Creadas con `CREATE TABLE IF NOT EXISTS`, sin romper tablas existentes:

- `api_sync_runs`
- `match_snapshots`
- `odds_memory_snapshots`
- `live_memory_snapshots`
- `pick_decisions`
- `pick_discards`
- `telegram_delivery_memory`
- `team_identity_cache`
- `data_memory_errors`
- `data_memory_retention_runs`

### 3. Integración segura
Conectado a:

- endpoints Cron Tick/Daily: registran ejecución en `api_sync_runs`
- Daily Run: guarda snapshots recientes de partidos y equipos
- creación/actualización de picks: registra decisión
- descartes Telegram de picks: registra motivo
- entregas Telegram: registra entrega sin guardar secrets

La memoria está envuelta en `safe_memory_call`, por lo que nunca debe romper Cron, Telegram ni la app si algo falla.

### 4. Admin Data Memory
Nueva vista protegida:

- `/admin/data-memory`
- `/api/admin/data-memory`
- `/api/admin/data-memory/cleanup`

Muestra:

- syncs recientes
- snapshots guardados
- decisiones de picks
- motivos de descarte
- entregas Telegram
- errores controlados
- política de retención
- estado de memoria

### 5. Variables preparadas
Añadidas a ejemplos de entorno:

```env
DATA_MEMORY_ENABLED=true
DATA_MEMORY_KEEP_DAYS=180
ODDS_SNAPSHOT_KEEP_DAYS=90
LIVE_SNAPSHOT_KEEP_DAYS=30
TELEGRAM_LOG_KEEP_DAYS=90
DATA_MEMORY_RAW_JSON=false
DATA_MEMORY_MAX_JSON_CHARS=6000
```

### 6. Herramientas de release limpio
Añadidas:

- `tools/build_clean_release.py`
- `tools/audit_release_zip.py`

Sirven para generar y auditar ZIPs limpios sin `.git`, `.venv`, cachés, DB locales, logs, ZIPs internos ni basura.

## Archivos tocados

- `app.py`
- `VERSION.txt`
- `.env.example`
- `.env.render.clean`
- `env.example`
- `engines/data_memory_engine.py`
- `templates/admin_data_memory.html`
- `tools/build_clean_release.py`
- `tools/audit_release_zip.py`
- `DATA_MEMORY_AUDIT_V721.md`

## Validación ejecutada

```text
python -m py_compile app.py engines/data_memory_engine.py: OK
python -m compileall -q app.py engines templates tools tests: OK
parseo Jinja templates: OK, 97 templates
prueba directa data_memory_engine con SQLite temporal: OK
ZIP limpio: OK
```

No se ejecutó `smoke_check.py` completo en este entorno porque no tiene Flask instalado. En local/Render se puede validar con:

```bash
pip install -r requirements.txt
python tools/smoke_check.py
python tools/validate_release.py
pytest -q
```

## Qué NO se tocó

- Render
- Cron Jobs
- Telegram automático
- Telegram solo fútbol
- calibración PRO
- `AUTOMATION_SECRET`
- `DB_PATH=/data/database.db`
- login/registro
- membresías
- combis hasta 15
- picks V719
- SHARK Advisor V720

## Cómo probar en Render

1. Subir ZIP V721.
2. Abrir `/api/runtime-version` y confirmar `V721_DATA_MEMORY_HISTORIC_SHARK`.
3. Ejecutar Cron Tick con secret real y comprobar `200`.
4. Ejecutar Daily Run con secret real y comprobar `200`.
5. Entrar como admin en `/admin/data-memory`.
6. Confirmar que aparecen syncs, Telegram y decisiones de picks tras ejecuciones reales.

## Pendiente dependiente de producción real

- La memoria crecerá cuando Daily/Tick funcionen con datos reales.
- Snapshots de cuotas/live dependerán de los proveedores y de los flujos activos.
- Para ML real aún falta fase posterior: resultados cerrados, grading automático y ROI histórico.

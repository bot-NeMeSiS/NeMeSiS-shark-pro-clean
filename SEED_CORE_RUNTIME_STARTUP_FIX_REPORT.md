# SEED Core Runtime Startup Fix

## Error de producción

Render mostraba el worker cayendo durante el arranque en `app.py`, dentro de `seed_core()`, al entrar en:

```python
with SEED_LOCK:
```

El síntoma operativo era:

- `SystemExit: 1`
- `Worker exiting`
- `Booting worker`

## Causa raíz

La aplicación tenía un punto de compatibilidad frágil entre versiones: el seed local usaba `_SEED_LOCK`, mientras el runtime desplegado por Render estaba entrando por una ruta que esperaba `SEED_LOCK`. Si `SEED_LOCK` no existía o quedaba sin inicializar antes de `seed_core()`, el worker podía morir durante el boot.

Además, el scheduler automático podía programarse durante el import de `app.py`. En Gunicorn/Render eso es peligroso porque el worker todavía está arrancando y no debe iniciar tareas pesadas ni cadenas que acaben invocando `seed_core()`.

## Corrección aplicada

Archivo afectado:

- `app.py`

Cambios principales:

- `SEED_LOCK` se define siempre antes de cualquier uso.
- `_SEED_LOCK` queda como alias compatible con código histórico.
- El lock pasa a ser reentrante con `threading.RLock()` para evitar bloqueos si una ruta de seed se reentra accidentalmente.
- `seed_core()` ahora repara el lock si una versión intermedia lo deja ausente.
- `seed_core()` mantiene guardas idempotentes con `_SEEDED_DB_PATH` y `_SEEDING_DB_PATH`.
- El scheduler de arranque ya no se ejecuta al importar `app.py` salvo activación explícita mediante `RUN_STARTUP_SCHEDULER_NOW=1`.
- En entorno Render/Gunicorn, el startup scheduler solo queda disponible si se activa explícitamente con variables de entorno.

## Líneas clave revisadas

- `app.py:65` define `SEED_LOCK`.
- `app.py:66` mantiene `_SEED_LOCK` como alias.
- `app.py:433` define `init_db()`.
- `app.py:1052` define `seed_core()`.
- `app.py:1054` protege la existencia de `SEED_LOCK`.
- `app.py:1060` entra en el lock ya inicializado.
- `app.py:2172` protege startup scheduler en Render/Gunicorn.
- `app.py:7276` impide ejecutar scheduler durante import salvo activación explícita.

## Verificaciones

Comando ejecutado:

```bash
python -m compileall app.py engines database_manager.py services
```

Resultado:

- OK.

Smoke test con base temporal:

- Import de `app.py`: OK.
- `seed_core()` primera ejecución: OK.
- `seed_core()` segunda ejecución: OK, sin repetir seed real.
- `SEED_LOCK` existe: OK.
- `_SEED_LOCK` apunta al mismo lock: OK.
- Sin `SystemExit`: OK.

Rutas validadas:

- `/api/health`: 200
- `/`: 200
- `/login`: 200
- `/admin-login`: 200
- `/dashboard`: 200
- `/telegram`: 200

## Estado final

La primera carga del worker ya no depende de un lock no inicializado ni dispara el scheduler automático durante el import. Render puede importar `app:app`, responder health checks y atender la portada sin entrar en bucle de workers.

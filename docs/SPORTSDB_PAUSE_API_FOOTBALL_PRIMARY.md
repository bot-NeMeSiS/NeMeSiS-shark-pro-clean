# API-FOOTBALL principal / TheSportsDB en pausa reversible

## Objetivo
Pausar **nuevas consultas** a TheSportsDB sin borrar claves, SQLite, asociaciones, registros ni los resúmenes previamente guardados. API-FOOTBALL sigue como origen principal de fixtures, directos, resultados, estadísticas y cuotas disponibles según el proveedor. Telegram, pagos y usuarios quedan fuera del cambio.

## Activación en producción (Render)
En los dos servicios activos (`nemesissharkpro` web y `telegram-auto-tick` cron) añadir **solo** estas variables, mediante merge, sin reemplazar el resto:
```env
THESPORTSDB_PAUSED=true
PRIMARY_FOOTBALL_DATA_PROVIDER=api_football
```
**No eliminar ni vaciar** `THESPORTSDB_KEY` / `THESPORTSDB_API_KEY`; la pausa filtra la credencial efectiva únicamente en código. `THESPORTSDB_PAUSED=false` reactiva peticiones después de comprobar permisos y coste.

## Protecciones
- `app.thesportsdb_key` y los adaptadores de highlights, perfiles, broadcast y código legacy obtienen clave efectiva vacía mientras la pausa está activa.
- El fallback de calendario TheSportsDB no se ejecuta si falla la vía primaria API-FOOTBALL.
- Los endpoints de sincronización de highlights devuelven `status=PAUSED`, `reason=provider_paused`, `external_calls=0`; los resúmenes existentes continúan legibles desde SQLite.
- El master cron omite la llamada a media sin afectar a los demás canales. Un runner legacy de media también se salta la tarea.
- El inventario mantiene `configured=true` si la clave está guardada, pero marca `paused=true` y `enabled=false`; API-FOOTBALL figura primera.

## Validación tras desplegar
1. Confirmar estado del último deploy y la versión en `/api/runtime-version`.
2. Verificar `/calendar`, `/live`, `/picks`, `/resumenes` sin 500; los resúmenes solo enseñan enlaces guardados y autorizados.
3. Comprobar que Render registra `highlights_result=provider_paused` y `external_calls=0` en el cron, sin afectar los ciclos de sports/Telegram.
4. Confirmar proveedor principal en panel de datos: API-FOOTBALL y TheSportsDB pausado.
5. Ejecutar `pytest -q tests/test_sportsdb_reversible_pause.py` y seguimiento de logs antes de cerrar.

**Importante:** pausar llamadas **no cancela** una suscripción de pago a TheSportsDB. Revisar la facturación con el proveedor por separado. No se eliminan credenciales ni datos.

## Reversión
En Render, cambiar únicamente `THESPORTSDB_PAUSED=false` (en web y cron); comprobar cuotas, derechos de uso y necesidad antes de reactivar. No hace falta restaurar ninguna base de datos.

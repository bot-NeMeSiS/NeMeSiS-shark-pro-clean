# TELEGRAM AUTO PICK DELIVERY FIX REPORT

Fecha: 2026-06-09  
Proyecto: NeMeSiS SHARK PRO  
Carpeta oficial: `C:\Users\aloha\OneDrive\Escritorio\NeMeSiS shark pro`

## 1. Causa raiz exacta

El envio manual funcionaba porque `/api/telegram/send` encolaba directamente un mensaje hacia `TELEGRAM_CHAT_ID` y despues procesaba la cola con `process_premium_telegram_queue()`.

El flujo automatico tenia dos problemas reales:

1. `refresh_auto_picks_basic()` solo calculaba candidatos, pero no guardaba picks automaticos en la tabla `picks`. El scheduler podia informar candidatos, pero Telegram no tenia picks nuevos reales que enviar si no existian picks publicados previamente.

2. La entrega automatica de picks dependia de suscriptores elegibles. Aunque existia `ensure_default_telegram_subscriber()`, el comportamiento no dejaba una regla explicita de producto: el canal global configurado en `TELEGRAM_CHAT_ID` debe recibir picks automaticos aunque no existan usuarios privados vinculados.

Ademas, la trazabilidad era insuficiente para distinguir:

- pick automatico generado
- pick elegible
- encolado automatico
- envio al canal
- envio privado
- duplicado evitado

## 2. Correccion aplicada

Archivo modificado:

- `app.py`

Cambios principales:

- `refresh_auto_picks_basic()` ahora puede persistir picks automaticos validos.
- Nueva funcion `ensure_auto_pick_from_recommendation(rec)`.
- Nueva funcion `telegram_auto_destinations(required_membership, include_global=True)`.
- Nueva funcion `enqueue_auto_pick_alerts(force=False, limit=6)`.
- `enqueue_daily_picks()` usa ahora destinos automaticos con canal global incluido.
- `telegram_scheduler_delivery()` ejecuta `enqueue_auto_pick_alerts()` cuando `auto_daily_picks` esta activo.
- `process_premium_telegram_queue()` registra envios con marca `[TELEGRAM]`.
- `telegram_diagnostics()` muestra `last_auto_pick` y `auto_pick_pending`.
- La accion admin `repair` y `/api/telegram/repair-automatic` tambien encolan picks automaticos.

## 3. Reglas nuevas del flujo automatico

Flujo corregido:

1. Scheduler ejecuta `auto_picks`.
2. Se revisan recomendaciones SHARK con score minimo.
3. Las recomendaciones validas se guardan como picks publicados de origen `auto_picks_scheduler`.
4. Scheduler ejecuta Telegram.
5. `enqueue_auto_pick_alerts()` busca picks elegibles.
6. Se encola siempre el canal global `TELEGRAM_CHAT_ID` si existe.
7. Se encolan privados vinculados si su membresia permite el pick.
8. `process_premium_telegram_queue()` envia.
9. La cola se marca como `sent` o `failed`.
10. El dedupe evita repetir el mismo pick al mismo destino.

## 4. Dedupe

Los picks automaticos usan:

`telegram_dedupe_key("auto_pick", pick_id, chat_id)`

Esto permite:

- Primer envio valido: se encola.
- Segundo intento real del mismo pick al mismo destino: se omite como duplicado.
- Otros destinos: pueden recibir el mismo pick si son elegibles.

## 5. Membresias

El canal global se trata como destino `ADMIN`, por lo que recibe todos los picks automaticos configurados.

Privados:

- FREE recibe solo lo permitido por su plan.
- PRO recibe FREE + PRO.
- ELITE recibe FREE + PRO + ELITE.
- ADMIN recibe todo.

## 6. Pruebas realizadas

Las pruebas se hicieron con base SQLite temporal y envio Telegram simulado para no llamar a la API real.

### Compileall

Resultado:

- `app.py`: OK
- `engines`: OK
- `database_manager.py`: OK
- `services`: OK

Nota: `python` no estaba en PATH; se uso el runtime local disponible.

### Envio manual

Prueba:

- Endpoint: `/api/telegram/send`
- Resultado: HTTP 200
- `processed=1`
- `sent=1`

### Auto pick al canal global sin privados

Prueba:

- Se creo un pick automatico publicado de prueba en base temporal.
- Se ejecuto `enqueue_auto_pick_alerts(force=False, limit=1)`.
- Se proceso la cola con envio simulado.

Resultado:

- Primer encolado automatico: `inserted=1`
- Procesado: `sent=1`
- Fallidos: `failed=0`
- Cola pendiente: `0`
- Ultimo `auto_pick`: `sent`
- `chat_id`: `-1003951459919`
- Errores de observabilidad: `0`

### Duplicado real

Prueba:

- Se ejecuto de nuevo el mismo encolado para el mismo pick y destino.

Resultado:

- Segundo encolado: `inserted=0`
- `skipped=1`
- Duplicados evitados: `1`

### Scheduler completo

Prueba:

- `telegram_scheduler_tick(force=True)`

Resultado:

- `scheduler_ok=true`
- `scheduler_sent=true`
- `result_sent=2`
- `result_failed=0`
- `last_auto_pick_status=sent`
- `pending=0`

## 7. Que no se pudo probar aqui

No se llamo a Telegram real desde esta prueba para evitar enviar mensajes reales durante la reparacion. El usuario ya habia confirmado que el endpoint manual real envia correctamente al canal:

- `ok=true`
- `processed=1`
- `sent=1`
- `chat_id=-1003951459919`

Como el automatico corregido usa el mismo `process_premium_telegram_queue()` y el mismo `telegram_send_http()`, la diferencia corregida estaba antes del envio: generacion, elegibilidad, destino global, encolado y dedupe.

## 8. Estado final

El flujo automatico queda reparado para:

- Canal global aunque no haya privados vinculados.
- Privados segun membresia si existen.
- Dedupe correcto.
- Cola `pending -> sent`.
- Diagnostico visible del ultimo pick automatico.
- Logs claros `[AUTO_PICKS]`, `[QUEUE]`, `[TELEGRAM]`.

## 9. Archivos entregados

- `TELEGRAM_AUTO_PICK_DELIVERY_FIX_REPORT.md`
- `TELEGRAM_AUTO_PICK_DELIVERY_DIFF.patch`
- `NEMESIS_SHARK_PRO_TELEGRAM_AUTO_PICK_DELIVERY_FIX_RENDER_READY.zip`

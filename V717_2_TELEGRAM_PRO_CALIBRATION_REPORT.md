# V717.2 — TELEGRAM PRO CALIBRATION

## Versión
`V717_2_TELEGRAM_PRO_CALIBRATION`

## Objetivo
Calibrar Telegram como servicio premium: revisar con frecuencia, enviar poco, enviar mejor y evitar spam. La lógica prioriza calidad, horario profesional, deduplicación, cuotas reales y límites de mensajes.

## Cambios principales

### Calibración PRO centralizada
Añadida configuración central en `app.py` mediante `telegram_pro_calibration()`:

- `TELEGRAM_MAX_MESSAGES_PER_HOUR=1`
- `TELEGRAM_MAX_MESSAGES_PER_DAY=8`
- `TELEGRAM_MAX_QUEUE_PER_TICK=3`
- `TELEGRAM_MAX_AUTO_PICKS_PER_TICK=2`
- `TELEGRAM_MAX_AUTO_PICKS_PER_DAY=4`
- `MIN_SHARK_SCORE_FOR_AUTO_SEND=75`
- `TELEGRAM_MIN_ODDS=1.40`
- `TELEGRAM_MAX_ODDS=4.50`
- `TELEGRAM_QUIET_START=00:30`
- `TELEGRAM_QUIET_END=09:30`
- `TELEGRAM_DAILY_SUMMARY_START=09:30`
- `TELEGRAM_DAILY_SUMMARY_END=12:30`
- `TELEGRAM_DAILY_PICKS_START=13:00`
- `TELEGRAM_DAILY_PICKS_END=20:30`

Todos los valores pueden sobrescribirse desde Render Environment si se desea.

### Horario silencioso
Los mensajes automáticos se retienen entre `00:30` y `09:30` hora España. Los mensajes manuales/admin/test pueden seguir forzándose con `force`.

### Resumen diario profesional
El resumen diario queda limitado a ventana profesional de mañana: `09:30` a `12:30`.

### Picks diarios profesionalizados
Los picks diarios se limitan a ventana de tarde/noche: `13:00` a `20:30`.

### Anti-spam por canal/usuario
El procesador de cola ahora respeta:

- máximo 1 mensaje automático por hora y destino
- máximo 8 mensajes automáticos por día y destino
- máximo 3 mensajes procesados por tick
- máximo 2 auto picks por tick
- máximo 4 auto picks diarios por destino

### Calidad mínima de picks
Los picks automáticos requieren:

- score mínimo 75
- cuota mínima 1.40
- cuota máxima 4.50
- no cuota pendiente
- no pick pendiente
- no partido antiguo/finalizado
- riesgo alto solo si la señal es muy fuerte

### Live alerts
Las alertas live también respetan horario silencioso para evitar mensajes nocturnos innecesarios.

### Diagnóstico admin
`telegram_diagnostics()` incluye ahora `pro_calibration` para ver la calibración activa desde admin sin exponer secretos.

### Defaults ajustados
`engines/telegram_delivery_engine.py` cambia defaults:

- daily matches: `10:00`
- daily picks: `13:30`
- max messages per hour: `1`

### Env examples
Actualizados:

- `.env.example`
- `env.example`
- `.env.render.clean`

con variables de calibración Telegram PRO.

## Archivos tocados

- `app.py`
- `VERSION.txt`
- `engines/telegram_delivery_engine.py`
- `.env.example`
- `env.example`
- `.env.render.clean`
- `V717_2_TELEGRAM_PRO_CALIBRATION_REPORT.md`

## Validación ejecutada

- `python -m py_compile app.py engines/telegram_delivery_engine.py engines/telegram_autonomous_delivery_engine.py`: OK
- `python -m compileall -q app.py engines services blueprints tools tests`: OK

`tools/smoke_check.py` no pudo completarse en este entorno porque falta Flask instalado (`No module named 'flask'`). El ZIP mantiene `requirements.txt`; en local/Render se valida con:

```bash
pip install -r requirements.txt
python tools/smoke_check.py
pytest -q
```

## Cron recomendado en Render

Telegram Tick:

```cron
*/15 * * * *
```

Daily Automation:

```cron
0 * * * *
```

La app revisa cada 15 minutos y actualiza cada hora, pero con esta calibración solo manda mensajes cuando toca y cuando hay señal de calidad.

## Calibración recomendada resultante

- 1 resumen diario por la mañana si hay datos
- 2-4 picks premium diarios como máximo
- 0-1 combi/pick resumen si hay suficientes selecciones válidas
- alertas live solo fuera de horario silencioso y si están activadas
- no spam, no cuota pendiente, no picks antiguos, no señales débiles

## Notas

No se ha tocado el secret real ni se ha guardado ningún valor sensible. Telegram/Cron siguen usando `AUTOMATION_SECRET` como antes.

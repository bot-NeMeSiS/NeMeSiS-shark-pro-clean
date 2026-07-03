# V888 Real Errors Sweep Report

Version local objetivo: `V888_REAL_ERRORS_SWEEP_TELEGRAM_MATCHES_PICKS_NAV_SENTINEL_FINAL`.

## Resultado ejecutivo

V888 queda preparada como barrido de errores reales sobre Telegram/Cron, rutas, texto visible, estados seguros, navegacion cliente/admin, SHARK/OpenAI, logos, pagos y Sentinel.

La produccion Render consultada en `https://bot-apuestas-crgf.onrender.com/api/runtime-version` no esta sirviendo V888. Devuelve `V883_VISUAL_COMPANY_WORKER_BOT_CONTINUOUS_IMPROVEMENT_FINAL`, por lo que cualquier certificacion visual de V888 en produccion queda bloqueada hasta desplegar el ZIP actual.

## Corregido en V888

- Fallback GET de SHARK corregido de `/api/shark/askq=` a `/api/shark/ask?q=`.
- Heartbeat de runtime en `base.html` corregido para no usar una expresion JS rota.
- Ruta `/favicon.ico` anadida con fallback ligero al logo SHARK.
- Login y registro reconstruidos con copy limpio en espanol y enlaces `?plan=` correctos.
- Admin Real Launch deja de afirmar Stripe o pagos operativos cuando no hay configuracion real.
- Mojibake visible en rutas de partidos/calendario limpiado.
- Enlace admin de highlights corregido de `syncforce=1` a `sync?force=1`.
- Sentinel incorpora reglas V888 para mismatch Render/local, Telegram Cron, picks/live, OpenAI safe mode, logo cache 0, pagos y navegacion.

## Probado local

- `python -m py_compile app.py`: OK.
- `python -m compileall app.py engines tools`: OK.
- `python tools/check_madrid_times.py`: OK.
- `python tools/check_v887_telegram_queue_skipped_hotfix.py`: OK.
- `python tools/check_v888_real_errors_sweep.py`: OK.
- Parseo Jinja: 161 templates OK.
- Smoke Flask real routes: 29 rutas OK.
- Smoke legacy: finaliza OK con avisos historicos.
- Continuous Sentinel static: score 10.0, 0 issues, 0 criticos.

## Bloqueadores reales

- Render real sigue en V883, no en V888.
- No se hizo deploy ni push automatico.
- No se envio Telegram real.
- No se probaron pagos reales.
- No se ejecutaron capturas browser/pixel-perfect.

## Estado de datos

No se inventaron partidos, picks, cuotas, resultados, minutos, escudos, pagos, usuarios ni envios Telegram. Cuando falta dato real, la app mantiene estados seguros como `Sin datos reales`, `Sin directos reales`, `Cuota pendiente`, `Seleccion pendiente`, `Pick en revision`, `No configurado` y `Modo seguro activo`.
